#!/bin/bash
# ============================================================
# AgenticCyOps — Full Baseline Verification
#
# Interactive domain selection, then runs benign E2E through
# all 3 configs, generates verification report + dashboard + PDF.
#
# Usage:
#   ./scripts/run_baseline.sh            # Interactive menu
#   ./scripts/run_baseline.sh cyberops   # Skip menu, run one domain
#   ./scripts/run_baseline.sh all        # Skip menu, run all
# ============================================================

set -eE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONDA_ENV="agenticcyops"
TOOL_BASE_PORT=9000
MMA_PORT=9100
PIDS=()

ALL_DOMAINS=("cyberops" "healthcare" "finance" "legal")

# ---- Interactive domain selection (if no argument) ----
if [ -z "$1" ]; then
    echo ""
    echo "  AgenticCyOps — Baseline Verification"
    echo "  ──────────────────────────────────────────────"
    echo ""
    echo "  Select domains to verify:"
    echo ""
    echo "    1) cyberops"
    echo "    2) healthcare"
    echo "    3) finance"
    echo "    4) legal"
    echo "    5) all (1-4)"
    echo "    q) quit"
    echo ""
    read -p "  Enter choices (e.g. 1 2 3, or 5 for all): " choices

    if [[ "$choices" == "q" ]]; then
        echo "  Cancelled."
        exit 0
    fi

    DOMAINS=()
    for c in $choices; do
        case "$c" in
            1) DOMAINS+=("cyberops") ;;
            2) DOMAINS+=("healthcare") ;;
            3) DOMAINS+=("finance") ;;
            4) DOMAINS+=("legal") ;;
            5) DOMAINS=("cyberops" "healthcare" "finance" "legal"); break ;;
        esac
    done

    if [ ${#DOMAINS[@]} -eq 0 ]; then
        echo "  No domains selected. Exiting."
        exit 0
    fi

elif [ "$1" = "all" ]; then
    DOMAINS=("${ALL_DOMAINS[@]}")
else
    DOMAINS=("$1")
fi

# ---- Cleanup on exit (kills ALL spawned processes) ----
cleanup() {
    echo ""
    echo "[cleanup] Stopping all background services..."

    # Kill tracked PIDs and their children
    for pid in "${PIDS[@]}"; do
        pkill -P "$pid" 2>/dev/null || true
        kill "$pid" 2>/dev/null || true
    done

    # Kill anything still holding tool/MMA ports
    for port in $(seq ${TOOL_BASE_PORT} $((TOOL_BASE_PORT + 15))) ${MMA_PORT}; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
    done

    wait 2>/dev/null || true
    echo "[cleanup] Done."
}
trap cleanup EXIT INT TERM

# ---- Helper: run python in conda env ----
run_py() {
    conda run --no-capture-output -n "$CONDA_ENV" python3 "$@"
}

# ---- Helper: wait for HTTP health ----
wait_for_health() {
    local url="$1"
    local name="$2"
    local timeout="${3:-60}"
    local elapsed=0
    while ! curl -s --max-time 1 "$url" > /dev/null 2>&1; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ $elapsed -ge $timeout ]; then
            echo "[FAIL] $name did not start within ${timeout}s"
            return 1
        fi
    done
    echo "[  ok] $name ready (${elapsed}s)"
}

# ---- Helper: check vLLM is running ----
check_vllm() {
    if ! curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo "ERROR: vLLM Primary server not running on port 8000."
        echo "Start it first: ./start_servers.sh (Group A)"
        echo ""
        exit 1
    fi
    echo "[  ok] vLLM Primary (port 8000) healthy"

    if curl -s --max-time 2 http://localhost:8002/health > /dev/null 2>&1; then
        echo "[  ok] vLLM V1 (port 8002) healthy"
    else
        echo "[ warn] V1 not running — consensus will be skipped"
    fi
}

# ---- Run baseline for one domain ----
run_domain_baseline() {
    local domain="$1"
    echo ""
    echo "============================================================"
    echo "  BASELINE VERIFICATION: ${domain}"
    echo "============================================================"
    echo ""

    # Step 0: Clean previous run data + stale ports
    echo "[step 0/7] Cleaning previous run data + stale ports..."
    rm -rf "logs/${domain}_baseline" 2>/dev/null || true
    rm -rf "results/baseline/${domain}" 2>/dev/null || true
    rm -rf "data/chromadb/${domain}" 2>/dev/null || true
    for port in $(seq ${TOOL_BASE_PORT} $((TOOL_BASE_PORT + 15))) ${MMA_PORT}; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
    done
    sleep 1

    # Step 1: Check vLLM
    echo "[step 1/7] Checking vLLM servers..."
    check_vllm

    # Step 2: Initialize ChromaDB
    echo ""
    echo "[step 2/7] Initializing ChromaDB for ${domain}..."
    run_py -m memory.chromadb_setup --domain "$domain" --db-path ./data/chromadb 2>&1 | tail -5

    # Step 3: Seed data
    echo ""
    echo "[step 3/7] Seeding memory collections..."
    run_py -m memory.seed_data --domain "$domain" --db-path ./data/chromadb 2>&1 | tail -15

    # Step 4: Start tool servers
    echo ""
    echo "[step 4/7] Starting ${domain} tool servers (port ${TOOL_BASE_PORT}+)..."
    run_py -m domains.${domain}.tools.start_all &
    PIDS+=($!)
    sleep 3

    # Wait for first tool to be healthy
    wait_for_health "http://localhost:${TOOL_BASE_PORT}/health" "${domain} tools" 30

    # Step 5: Start MMA gateway
    echo ""
    echo "[step 5/7] Starting MMA gateway (port ${MMA_PORT})..."
    run_py -m memory.mma_gateway --domain "$domain" --port $MMA_PORT &
    PIDS+=($!)
    wait_for_health "http://localhost:${MMA_PORT}/health" "MMA gateway" 30 || true

    # Step 6: Run benign E2E for each config
    echo ""
    echo "[step 6/7] Running benign E2E tests..."
    echo ""

    mkdir -p "logs/${domain}_baseline"

    for config in flat acl_hardened agenticcyops; do
        echo "  --- ${domain} / ${config} ---"
        run_py -c "
import asyncio, json, sys
sys.path.insert(0, '.')
from logging_utils import ExperimentLogger
from host.orchestrator import SOARHost
from host.manifest_enforcer import ManifestEnforcer
from mcp_servers.server_registry import ServerRegistry
from agents.monitor_agent import MonitorAgent
from agents.analyze_agent import AnalyzeAgent
from agents.admin_agent import AdminAgent
from agents.report_agent import ReportAgent

async def run():
    domain = '${domain}'
    config = '${config}'

    logger = ExperimentLogger(
        eval_name='${domain}_baseline',
        domain=domain,
        config=config,
        model='Qwen3-235B',
    )
    logger.set_trial(ap='benign', variant=1, trial=1)

    # Load manifests
    enforcer = ManifestEnforcer(domain=domain, logger=logger)

    # Load tool registry (tools already running)
    registry = ServerRegistry(domain=domain, logger=logger)
    registry.load_tools()
    # Map ports manually since tools are already started
    import importlib
    port = ${TOOL_BASE_PORT}
    for tool_id in sorted(registry._servers.keys()):
        registry._ports[tool_id] = port
        port += 1

    all_schemas = registry.get_all_schemas()

    # Create agents with config-appropriate tool visibility
    agents = {}
    for phase, AgentClass in [('monitor', MonitorAgent), ('analyze', AnalyzeAgent),
                               ('admin', AdminAgent), ('report', ReportAgent)]:
        manifest = enforcer.get_manifest(phase)
        phase_schemas = registry.get_phase_schemas(manifest.get('allowed_tools', []))
        agents[phase] = AgentClass(
            domain=domain,
            config=config,
            manifest=manifest,
            tool_schemas=phase_schemas,
            all_tool_schemas=all_schemas,
            logger=logger,
        )

    # Create consensus validator (for agenticcyops config)
    consensus = None
    if config == 'agenticcyops':
        try:
            from consensus.validator import ConsensusValidator
            consensus = ConsensusValidator(
                config_name='default_consensus',
                logger=logger,
            )
            print('    Consensus: V1+V2+V4 loaded')
        except Exception as e:
            print(f'    Consensus: skipped ({e})')

    # Create host
    host = SOARHost(
        domain=domain,
        config=config,
        tool_registry=registry,
        consensus=consensus,
        agents=agents,
        logger=logger,
    )

    # Load domain-appropriate benign incident
    import json as _json
    from pathlib import Path as _Path
    _benign_file = _Path(f'domains/{domain}/payloads/benign_alerts.json')
    if not _benign_file.exists():
        _benign_file = _Path(f'domains/{domain}/payloads/benign_workflows.json')
    if _benign_file.exists():
        with open(_benign_file) as _f:
            _payloads = _json.load(_f)
        incident = _payloads[0].get('trigger', _payloads[0])
        if 'incident_id' not in incident:
            incident['incident_id'] = f'{domain}-BENIGN-001'
    else:
        incident = {
            'incident_id': f'{domain}-BENIGN-001',
            'alert_type': 'generic_alert',
            'timestamp': '2026-04-09T10:00:00Z',
            'initial_severity': 'medium',
            'description': f'Benign test incident for {domain} domain.',
        }

    try:
        result = await host.run_incident(incident)
        phases = list(result.get('phases', {}).keys())
        print(f'    Completed phases: {phases}')
        print(f'    Log: {logger.log_file}')
    except Exception as e:
        print(f'    ERROR: {e}')
    finally:
        logger.close()

asyncio.run(run())
" 2>&1 | grep -v "TqdmWarning\|tqdm\|^$"
        echo ""
    done

    # Step 7: Verification report
    echo "[step 7/7] Generating verification report..."
    echo ""
    run_py -m analysis.verify_baseline --domain "$domain" --config all 2>&1

    # Dashboard
    echo ""
    echo "Generating baseline dashboard + report..."
    mkdir -p "results/baseline/${domain}"
    run_py -m analysis.baseline_dashboard --domain "$domain" --output "results/baseline/${domain}/" 2>&1 || true
    run_py -m analysis.generate_report --domain "$domain" --output "results/baseline/${domain}/" 2>&1 || true

    echo ""
    echo "============================================================"
    echo "  ${domain} BASELINE COMPLETE"
    echo "============================================================"

    # Stop domain-specific services before next domain
    for pid in "${PIDS[@]}"; do
        pkill -P "$pid" 2>/dev/null || true
        kill "$pid" 2>/dev/null || true
    done
    for port in $(seq ${TOOL_BASE_PORT} $((TOOL_BASE_PORT + 15))) ${MMA_PORT}; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
    done
    wait 2>/dev/null || true
    PIDS=()
}

# ---- Main ----
echo ""
echo "============================================================"
echo "  AgenticCyOps — Baseline Verification"
echo "  Domains: ${DOMAINS[*]}"
echo "============================================================"

for d in "${DOMAINS[@]}"; do
    run_domain_baseline "$d"
done

# Readiness gate
if [ ${#DOMAINS[@]} -gt 1 ]; then
    echo ""
    echo "============================================================"
    echo "  READINESS GATE"
    echo "============================================================"
    run_py -m analysis.verify_baseline --domain all --config all 2>&1
fi

echo ""
echo "Done. Results in results/baseline/"
