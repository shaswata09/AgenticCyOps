"""
Memory Management Agent (MMA) Gateway -- FastAPI server.

Mediates ALL memory access in the AgenticCyOps configuration.
Enforces P4 (write-boundary filtering) and P5 (phase-partitioned access control).

Endpoints:
    POST /memory/read   -- query a collection (checks P5)
    POST /memory/write  -- write to a collection (checks P5 then P4)
    GET  /memory/list   -- list accessible stores for a phase

Usage:
    python -m memory.mma_gateway --domain cyberops --port 9100
"""

import argparse
import json
import time
from pathlib import Path
from typing import Optional

import chromadb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import BASE_DIR
from logging_utils import ExperimentLogger
from memory.access_control import AccessController
from memory.write_filter import WriteFilter


# ------------------------------------------------------------------ #
#  Request / Response schemas
# ------------------------------------------------------------------ #

class MemoryReadRequest(BaseModel):
    phase: str
    store_id: str
    query: str
    n_results: int = 5


class MemoryWriteRequest(BaseModel):
    phase: str
    store_id: str
    document: str
    doc_id: str
    incident_evidence: str
    metadata: Optional[dict] = None


class MemoryListRequest(BaseModel):
    phase: str
    mode: str = "read"  # "read" or "write"


class MemoryReadResponse(BaseModel):
    store_id: str
    documents: list[str]
    metadatas: list[dict]
    distances: list[float]


class MemoryWriteResponse(BaseModel):
    store_id: str
    doc_id: str
    accepted: bool
    similarity_score: float


class MemoryListResponse(BaseModel):
    phase: str
    mode: str
    accessible_stores: list[str]


# ------------------------------------------------------------------ #
#  Application factory
# ------------------------------------------------------------------ #

def create_app(
    domain: str = "cyberops",
    db_path: str = "./data/chromadb",
    embedding_model_path: str | None = None,
    similarity_threshold: float = 0.5,
) -> FastAPI:
    """Build and return the FastAPI application with all dependencies wired up.

    Args:
        domain: Domain identifier.
        db_path: Base path to ChromaDB persistence.
        embedding_model_path: Path to embedding model for WriteFilter.
        similarity_threshold: Cosine similarity threshold for P4 filtering.

    Returns:
        Configured FastAPI app.
    """
    if embedding_model_path is None:
        embedding_model_path = str(
            BASE_DIR / "models" / "Qwen" / "Qwen3-Embedding-8B"
        )

    app = FastAPI(
        title="MMA Gateway",
        description="Memory Management Agent -- mediates all memory access in AgenticCyOps.",
        version="0.1.0",
    )

    # -- Dependencies ---------------------------------------------------

    access_controller = AccessController(domain=domain)

    write_filter = WriteFilter(
        embedding_model_path=embedding_model_path,
        similarity_threshold=similarity_threshold,
    )

    chroma_path = Path(db_path) / domain
    chroma_client = chromadb.PersistentClient(path=str(chroma_path))

    # Load collection name mapping: store_id -> collection_name
    collections_config_path = (
        BASE_DIR / "domains" / domain / "configs" / "memory_collections.json"
    )
    with open(collections_config_path, "r") as f:
        coll_data = json.load(f)
    store_id_to_name: dict[str, str] = {
        c["id"]: c["name"] for c in coll_data["collections"]
    }

    logger = ExperimentLogger(
        eval_name="mma_gateway",
        domain=domain,
        config="agenticcyops",
        model="Qwen3-Embedding-8B",
    )

    # -- Helpers --------------------------------------------------------

    def _get_collection(store_id: str):
        coll_name = store_id_to_name.get(store_id)
        if coll_name is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown store_id: {store_id}",
            )
        return chroma_client.get_or_create_collection(name=coll_name)

    # -- Endpoints ------------------------------------------------------

    @app.post("/memory/read", response_model=MemoryReadResponse)
    def memory_read(req: MemoryReadRequest):
        """Query a collection. Enforces P5 access control."""
        start = time.perf_counter()

        # P5 check
        if not access_controller.can_read(req.phase, req.store_id):
            latency = (time.perf_counter() - start) * 1000
            logger.log_memory_read(
                agent=req.phase,
                store=req.store_id,
                auth_decision="deny",
                mechanism="P5_access_control",
                latency_ms=latency,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Phase '{req.phase}' is not allowed to read from '{req.store_id}'.",
            )

        collection = _get_collection(req.store_id)
        results = collection.query(
            query_texts=[req.query],
            n_results=req.n_results,
        )

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        latency = (time.perf_counter() - start) * 1000
        logger.log_memory_read(
            agent=req.phase,
            store=req.store_id,
            auth_decision="allow",
            mechanism="P5_access_control",
            latency_ms=latency,
            num_results=len(documents),
        )

        return MemoryReadResponse(
            store_id=req.store_id,
            documents=documents,
            metadatas=metadatas,
            distances=distances,
        )

    @app.post("/memory/write", response_model=MemoryWriteResponse)
    def memory_write(req: MemoryWriteRequest):
        """Write to a collection. Enforces P5 access control then P4 write filtering."""
        start = time.perf_counter()

        # P5 check
        if not access_controller.can_write(req.phase, req.store_id):
            latency = (time.perf_counter() - start) * 1000
            logger.log_memory_write(
                agent=req.phase,
                store=req.store_id,
                auth_decision="deny",
                mechanism="P5_access_control",
                latency_ms=latency,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Phase '{req.phase}' is not allowed to write to '{req.store_id}'.",
            )

        # P4 write-boundary filter
        allowed, score = write_filter.validate_write(
            content=req.document,
            incident_evidence=req.incident_evidence,
        )

        if not allowed:
            latency = (time.perf_counter() - start) * 1000
            logger.log_memory_write(
                agent=req.phase,
                store=req.store_id,
                auth_decision="deny",
                mechanism="P4_memory_integrity",
                latency_ms=latency,
                payload=req.document,
                cosine_similarity=score,
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Write rejected by P4 filter: cosine similarity {score:.4f} "
                    f"< threshold {write_filter.threshold}."
                ),
            )

        # Write accepted -- upsert into ChromaDB
        collection = _get_collection(req.store_id)
        metadata = req.metadata or {}
        metadata["phase"] = req.phase
        metadata["store_id"] = req.store_id

        collection.upsert(
            ids=[req.doc_id],
            documents=[req.document],
            metadatas=[metadata],
        )

        latency = (time.perf_counter() - start) * 1000
        logger.log_memory_write(
            agent=req.phase,
            store=req.store_id,
            auth_decision="allow",
            mechanism="P4_memory_integrity",
            latency_ms=latency,
            payload=req.document,
            cosine_similarity=score,
        )

        return MemoryWriteResponse(
            store_id=req.store_id,
            doc_id=req.doc_id,
            accepted=True,
            similarity_score=round(score, 4),
        )

    @app.get("/memory/list", response_model=MemoryListResponse)
    def memory_list(phase: str, mode: str = "read"):
        """List accessible stores for a given phase and mode."""
        stores = access_controller.accessible_stores(phase, mode)

        logger.log(
            source=phase,
            destination="mma_gateway",
            action="memory_list",
            extra={"mode": mode, "accessible_stores": stores},
        )

        return MemoryListResponse(
            phase=phase,
            mode=mode,
            accessible_stores=stores,
        )

    return app


# ------------------------------------------------------------------ #
#  CLI entry point
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(
        description="MMA Gateway -- FastAPI server for AgenticCyOps memory access.",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="cyberops",
        help="Domain identifier (default: cyberops).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9100,
        help="Port to listen on (default: 9100).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="./data/chromadb",
        help="Base path for ChromaDB persistence (default: ./data/chromadb).",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path to embedding model (default: models/Qwen/Qwen3-Embedding-8B).",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.5,
        help="Cosine similarity threshold for P4 write filter (default: 0.5).",
    )
    args = parser.parse_args()

    import uvicorn

    app = create_app(
        domain=args.domain,
        db_path=args.db_path,
        embedding_model_path=args.model_path,
        similarity_threshold=args.similarity_threshold,
    )

    print(f"Starting MMA Gateway on {args.host}:{args.port}")
    print(f"Domain: {args.domain}")
    print(f"ChromaDB path: {args.db_path}/{args.domain}/")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
