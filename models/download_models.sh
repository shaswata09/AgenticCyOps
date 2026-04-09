#!/bin/bash
# ============================================================
# AgenticCyOps — Model Download Script
# ============================================================
# Run from the directory where you want models stored.
# Creates: ./Qwen/Qwen3-235B-A22B-Instruct-2507/
#          ./zai-org/GLM-4.7/
#          ./Qwen/Qwen3-32B/
#          ./mistralai/Mistral-Small-3.2-24B-Instruct-2506/
#          ./meta-llama/Llama-4-Scout-17B-16E-Instruct/
#          ./Qwen/Qwen3-Embedding-8B/
#
# Hardware target: 6× H200 (4 NVLink + 2 standalone)
# Estimated total download: ~550 GB
# ============================================================

set -e

# ---- Prerequisites ----
pip install "huggingface_hub>=0.28.0,<1.0" hf_transfer --quiet

# Enable Rust-based parallel downloads (much faster)
export HF_HUB_ENABLE_HF_TRANSFER=1

# Login — will prompt for your HF token
huggingface-cli whoami || huggingface-cli login

BASE_DIR="$(pwd)"

echo ""
echo "============================================"
echo " AgenticCyOps Model Download"
echo " Target directory: $BASE_DIR"
echo " Estimated total size: ~550 GB"
echo "============================================"
echo ""

# ============================================================
# 1. PRIMARY AGENTS + HOST
#    Qwen3-235B-A22B-Instruct (MoE, ~22B active)
#    GPU assignment: GPU 0-1 (NVLink pair)
#    VRAM: ~120GB FP8 across 2× H200
#    vLLM: --tensor-parallel-size 2 --tool-call-parser hermes
# ============================================================
echo "[1/6] Downloading Qwen3-235B-A22B-Instruct (~120 GB)..."
huggingface-cli download Qwen/Qwen3-235B-A22B-Instruct-2507 \
  --local-dir "$BASE_DIR/Qwen/Qwen3-235B-A22B-Instruct-2507" \
  --local-dir-use-symlinks False

# ============================================================
# 2. DIVERSITY AGENTS (second model family for comparison runs)
#    GLM-4.7 (Zhipu AI) — S-tier, #1 Chatbot Arena open-source
#    GPU assignment: GPU 2-3 (NVLink pair)
#    VRAM: ~260GB BF16 across 2× H200
#    NOTE: Requires vLLM nightly (pip install -U vllm --pre)
#    vLLM: --tensor-parallel-size 2 --tool-call-parser glm47
# ============================================================
echo "[2/6] Downloading GLM-4.7 (~260 GB)..."
huggingface-cli download zai-org/GLM-4.7 \
  --local-dir "$BASE_DIR/zai-org/GLM-4.7" \
  --local-dir-use-symlinks False

# ============================================================
# 3. VALIDATOR 1 (same Qwen family, smaller = different failure mode)
#    Qwen3-32B (dense, unified thinking/non-thinking mode)
#    GPU assignment: GPU 4 (shared, ~45% utilization)
#    VRAM: ~64GB BF16, single GPU
#    vLLM: --gpu-memory-utilization 0.45
# ============================================================
echo "[3/6] Downloading Qwen3-32B (~64 GB)..."
huggingface-cli download Qwen/Qwen3-32B \
  --local-dir "$BASE_DIR/Qwen/Qwen3-32B" \
  --local-dir-use-symlinks False

# ============================================================
# 4. VALIDATOR 2 (Mistral family — third model family)
#    Mistral-Small-3.2-24B-Instruct
#    GPU assignment: GPU 4 (shared, ~45% utilization)
#    VRAM: ~48GB BF16, single GPU
#    vLLM: --gpu-memory-utilization 0.45
# ============================================================
echo "[4/6] Downloading Mistral-Small-3.2-24B-Instruct (~48 GB)..."
huggingface-cli download mistralai/Mistral-Small-3.2-24B-Instruct-2506 \
  --local-dir "$BASE_DIR/mistralai/Mistral-Small-3.2-24B-Instruct-2506" \
  --local-dir-use-symlinks False

# ============================================================
# 5. VALIDATOR 3 (Meta Llama family — fourth model family)
#    Llama-4-Scout-17B-16E-Instruct (MoE, 109B total, 17B active)
#    GPU assignment: GPU 5
#    VRAM: ~55GB FP8, single GPU
#    vLLM: --gpu-memory-utilization 0.85
# ============================================================
echo "[5/6] Downloading Llama-4-Scout-17B-16E-Instruct (~55 GB)..."
huggingface-cli download meta-llama/Llama-4-Scout-17B-16E-Instruct \
  --local-dir "$BASE_DIR/meta-llama/Llama-4-Scout-17B-16E-Instruct" \
  --local-dir-use-symlinks False

# ============================================================
# 6. EMBEDDING MODEL (for ChromaDB / RAG memory layer)
#    Qwen3-Embedding-8B — #1 MTEB multilingual leaderboard
#    Runs on CPU or any GPU (~16GB BF16)
#    Used by: Memory Management Agent for semantic search,
#             write-boundary filtering (cosine similarity checks)
#    Supports Matryoshka dimensions (32–4096), last-token pooling
# ============================================================
echo "[6/6] Downloading Qwen3-Embedding-8B (~16 GB)..."
huggingface-cli download Qwen/Qwen3-Embedding-8B \
  --local-dir "$BASE_DIR/Qwen/Qwen3-Embedding-8B" \
  --local-dir-use-symlinks False

echo ""
echo "============================================"
echo " All downloads complete!"
echo "============================================"
echo ""
echo "Directory structure:"
echo "--------------------------------------------"
find "$BASE_DIR" -maxdepth 2 -type d | sort
echo ""
echo "Disk usage per model:"
echo "--------------------------------------------"
du -sh "$BASE_DIR"/Qwen/Qwen3-235B-A22B-Instruct-2507 2>/dev/null || true
du -sh "$BASE_DIR"/zai-org/GLM-4.7 2>/dev/null || true
du -sh "$BASE_DIR"/Qwen/Qwen3-32B 2>/dev/null || true
du -sh "$BASE_DIR"/mistralai/Mistral-Small-3.2-24B-Instruct-2506 2>/dev/null || true
du -sh "$BASE_DIR"/meta-llama/Llama-4-Scout-17B-16E-Instruct 2>/dev/null || true
du -sh "$BASE_DIR"/Qwen/Qwen3-Embedding-8B 2>/dev/null || true
echo ""
echo "Total:"
du -sh "$BASE_DIR"
echo ""
echo "============================================"
echo " GPU Assignment Reference"
echo "============================================"
echo ""
echo "  GPU 0-1 (NVLink) : Qwen3-235B-A22B  [Primary agents + Host]"
echo "  GPU 2-3 (NVLink) : GLM-4.7          [Diversity agents]"
echo "  GPU 4             : Qwen3-32B + Mistral-Small-3.2  [Validators 1 & 2]"
echo "  GPU 5             : Llama-4-Scout    [Validator 3]"
echo "  CPU / any GPU     : Qwen3-Embedding-8B [Embedding for ChromaDB]"
echo ""
echo " Proprietary (API only, not downloaded):"
echo "  GPT-4o            : TAMAS benchmark baseline (~\$50 API budget)"
echo ""
echo "============================================"
echo " vLLM Serve Commands (copy-paste ready)"
echo "============================================"
echo ""
echo "# NOTE: GLM-4.7 requires vLLM nightly:"
echo "#   pip install -U vllm --pre --index-url https://pypi.org/simple --extra-index-url https://wheels.vllm.ai/nightly"
echo ""
echo "# Terminal 1 — Primary agents (GPU 0-1)"
echo "CUDA_VISIBLE_DEVICES=0,1 vllm serve $BASE_DIR/Qwen/Qwen3-235B-A22B-Instruct-2507 \\"
echo "  --tensor-parallel-size 2 \\"
echo "  --enable-auto-tool-choice \\"
echo "  --tool-call-parser hermes \\"
echo "  --gpu-memory-utilization 0.9 \\"
echo "  --port 8000"
echo ""
echo "# Terminal 2 — Diversity agents (GPU 2-3)"
echo "CUDA_VISIBLE_DEVICES=2,3 vllm serve $BASE_DIR/zai-org/GLM-4.7 \\"
echo "  --tensor-parallel-size 2 \\"
echo "  --enable-auto-tool-choice \\"
echo "  --tool-call-parser glm47 \\"
echo "  --reasoning-parser glm45 \\"
echo "  --gpu-memory-utilization 0.9 \\"
echo "  --port 8001"
echo ""
echo "# Terminal 3 — Validator 1 (GPU 4, shared)"
echo "CUDA_VISIBLE_DEVICES=4 vllm serve $BASE_DIR/Qwen/Qwen3-32B \\"
echo "  --gpu-memory-utilization 0.45 \\"
echo "  --port 8002"
echo ""
echo "# Terminal 4 — Validator 2 (GPU 4, shared)"
echo "CUDA_VISIBLE_DEVICES=4 vllm serve $BASE_DIR/mistralai/Mistral-Small-3.2-24B-Instruct-2506 \\"
echo "  --gpu-memory-utilization 0.45 \\"
echo "  --port 8003"
echo ""
echo "# Terminal 5 — Validator 3 (GPU 5)"
echo "CUDA_VISIBLE_DEVICES=5 vllm serve $BASE_DIR/meta-llama/Llama-4-Scout-17B-16E-Instruct \\"
echo "  --gpu-memory-utilization 0.85 \\"
echo "  --port 8004"
echo ""