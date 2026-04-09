#!/bin/bash
# ============================================================
# AgenticCyOps — Full Baseline Verification
#
# 1. Choose model group (A-E)
# 2. Verify required servers are running
# 3. Choose domains
# 4. Run baseline, store in results/baseline/{group}/{domain}/
#
# Usage:
#   ./scripts/run_baseline.sh            # Interactive
#   ./scripts/run_baseline.sh A 5        # Group A, all domains
#   ./scripts/run_baseline.sh A 1        # Group A, cyberops only
#   ./scripts/run_baseline.sh B 2 3      # Group B, healthcare + finance
# ============================================================

set -eE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONDA_ENV="agenticcyops"
TOOL_BASE_PORT=9000
MMA_PORT=9100
PIDS=()

ALL_DOMAINS=("cyberops" "healthcare" "finance" "legal")

# ---- Group definitions ----
# Each group: display name, primary LLM port, required ports, consensus config
declare -A GROUP_NAMES GROUP_PRIMARY GROUP_PORTS GROUP_CONSENSUS GROUP_DESC

GROUP_NAMES[A]="Group A: Main Experiments (4 validator families)"
GROUP_PRIMARY[A]="http://localhost:8000/v1"
GROUP_PORTS[A]="8000 8002 8005"
GROUP_CONSENSUS[A]="default_consensus"
GROUP_DESC[A]="Qwen3-235B (8000) + V1 Qwen3-32B (8002) + V2 DeepSeek-R1 (8005) + V4 Claude + V6 GPT-4o (t=3/4)"

GROUP_NAMES[B]="Group B: GLM Diversity"
GROUP_PRIMARY[B]="http://localhost:8001/v1"
GROUP_PORTS[B]="8001 8002 8005"
GROUP_CONSENSUS[B]="default_consensus"
GROUP_DESC[B]="GLM-4.7-FP8 (8001) + V1(Qwen) + V2(DeepSeek) + V4(Claude) + V6(GPT-4o) [t=3/4]"

GROUP_NAMES[C]="Group C: Validator Same-Family"
GROUP_PRIMARY[C]="http://localhost:8000/v1"
GROUP_PORTS[C]="8000 8002"
GROUP_CONSENSUS[C]="same_family"
GROUP_DESC[C]="Qwen3-235B (8000) + V1 Qwen3-32B x3 (8002) — same-family consensus [t=2/3]"

GROUP_NAMES[D]="Group D: Validator All-Local + API"
GROUP_PRIMARY[D]="http://localhost:8004/v1"
GROUP_PORTS[D]="8004 8002 8005"
GROUP_CONSENSUS[D]="default_consensus"
GROUP_DESC[D]="Llama-4-Scout (8004) + V1(Qwen) + V2(DeepSeek) + V4(Claude) + V6(GPT-4o) [t=3/4]"

GROUP_NAMES[E]="Group E: With Mistral"
GROUP_PRIMARY[E]="http://localhost:8000/v1"
GROUP_PORTS[E]="8000 8002 8003"
GROUP_CONSENSUS[E]="with_mistral"
GROUP_DESC[E]="Qwen3-235B (8000) + V1(Qwen) + V5(Mistral) + V4(Claude) + V6(GPT-4o) [t=3/4]"

GROUP_NAMES[F]="Group F: Full Local Diversity"
GROUP_PRIMARY[F]="http://localhost:8000/v1"
GROUP_PORTS[F]="8000 8002 8005"
GROUP_CONSENSUS[F]="full_diversity"
GROUP_DESC[F]="Qwen3-235B (8000) + ALL validators: V1-V6 (6 families) [t=4/7]"

GROUP_NAMES[G]="Group G: Claude as Primary"
GROUP_PRIMARY[G]="anthropic"
GROUP_PORTS[G]="8002 8005"
GROUP_CONSENSUS[G]="default_no_claude"
GROUP_DESC[G]="Claude Sonnet (API primary) + V1(Qwen) + V2(DeepSeek) + V6(GPT-4o) [t=2/3, no Claude as validator when it's primary]"

ALL_GROUPS=("A" "B" "C" "D" "E" "F" "G")

# ---- Interactive or CLI ----
if [ -z "$1" ]; then
    echo ""
    echo "  AgenticCyOps — Baseline Verification"
    echo "  ──────────────────────────────────────────────"
    echo ""
    echo "  Step 1: Select Model Group"
    echo ""
    for g in "${ALL_GROUPS[@]}"; do
        echo "    $g) ${GROUP_NAMES[$g]}"
        echo "       ${GROUP_DESC[$g]}"
        echo ""
    done
    read -p "  Select group [A]: " group_choice
    GROUP="${group_choice:-A}"
    GROUP="${GROUP^^}"  # uppercase

    echo ""
    echo "  Step 2: Select Domains"
    echo ""
    echo "    1) cyberops"
    echo "    2) healthcare"
    echo "    3) finance"
    echo "    4) legal"
    echo "    5) all (1-4)"
    echo ""
    read -p "  Enter choices (e.g. 1 2 3, or 5 for all): " domain_choices

    DOMAINS=()
    for c in $domain_choices; do
        case "$c" in
            1) DOMAINS+=("cyberops") ;;
            2) DOMAINS+=("healthcare") ;;
            3) DOMAINS+=("finance") ;;
            4) DOMAINS+=("legal") ;;
            5) DOMAINS=("cyberops" "healthcare" "finance" "legal"); break ;;
        esac
    done
    [ ${#DOMAINS[@]} -eq 0 ] && echo "  No domains selected." && exit 0
else
    GROUP="${1^^}"
    shift
    if [ -z "$1" ]; then
        DOMAINS=("${ALL_DOMAINS[@]}")
    else
        DOMAINS=()
        for c in "$@"; do
            case "$c" in
                1|cyberops) DOMAINS+=("cyberops") ;;
                2|healthcare) DOMAINS+=("healthcare") ;;
                3|finance) DOMAINS+=("finance") ;;
                4|legal) DOMAINS+=("legal") ;;
                5|all) DOMAINS=("cyberops" "healthcare" "finance" "legal"); break ;;
            esac
        done
    fi
fi

# Validate group
if [ -z "${GROUP_NAMES[$GROUP]}" ]; then
    echo "  Unknown group: $GROUP. Use A/B/C/D/E."
    exit 1
fi

LLM_URL="${GROUP_PRIMARY[$GROUP]}"
CONSENSUS_CONFIG="${GROUP_CONSENSUS[$GROUP]}"
REQUIRED_PORTS="${GROUP_PORTS[$GROUP]}"
RESULT_DIR="results/baseline/group_${GROUP}"

run_py() {
    conda run --no-capture-output -n "$CONDA_ENV" python3 "$@"
}

wait_for_health() {
    local url="$1" name="$2" timeout="${3:-60}" elapsed=0
    while ! curl -s --max-time 1 "$url" > /dev/null 2>&1; do
        sleep 1; elapsed=$((elapsed + 1))
        [ $elapsed -ge $timeout ] && echo "[FAIL] $name timeout" && return 1
    done
    echo "[  ok] $name ready (${elapsed}s)"
}

cleanup() {
    echo ""
    echo "[cleanup] Stopping background services..."
    for pid in "${PIDS[@]}"; do
        pkill -P "$pid" 2>/dev/null || true
        kill "$pid" 2>/dev/null || true
    done
    for port in $(seq ${TOOL_BASE_PORT} $((TOOL_BASE_PORT + 15))) ${MMA_PORT}; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
    done
    wait 2>/dev/null || true
    echo "[cleanup] Done."
}
trap cleanup EXIT INT TERM

echo ""
echo "============================================================"
echo "  AgenticCyOps — Baseline Verification"
echo "  ${GROUP_NAMES[$GROUP]}"
echo "  ${GROUP_DESC[$GROUP]}"
echo "  Domains: ${DOMAINS[*]}"
echo "  Results: ${RESULT_DIR}/"
echo "============================================================"

# ---- Check required vLLM servers ----
echo ""
echo "[check] Verifying required servers for ${GROUP_NAMES[$GROUP]}..."
all_up=true
for port in $REQUIRED_PORTS; do
    if curl -s --max-time 2 http://localhost:$port/health > /dev/null 2>&1; then
        echo "[  ok] Port $port healthy"
    else
        echo "[FAIL] Port $port not running"
        all_up=false
    fi
done

if [ "$all_up" = false ]; then
    echo ""
    echo "  ERROR: Required servers not running."
    echo "  Start them with: ./start_servers.sh"
    echo "  Required ports: $REQUIRED_PORTS"
    exit 1
fi

# ---- Run baseline per domain ----
run_domain_baseline() {
    local domain="$1"
    echo ""
    echo "============================================================"
    echo "  BASELINE: ${domain} / Group ${GROUP}"
    echo "============================================================"

    # Clean previous data for this group+domain
    echo "[step 0/7] Cleaning previous run data + stale ports..."
    rm -rf "logs/${domain}_baseline_${GROUP}" 2>/dev/null || true
    rm -rf "${RESULT_DIR}/${domain}" 2>/dev/null || true
    rm -rf "data/chromadb/${domain}" 2>/dev/null || true
    for port in $(seq ${TOOL_BASE_PORT} $((TOOL_BASE_PORT + 15))) ${MMA_PORT}; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
    done
    sleep 1

    # ChromaDB
    echo "[step 2/7] Initializing ChromaDB for ${domain}..."
    run_py -m memory.chromadb_setup --domain "$domain" --db-path ./data/chromadb 2>&1 | tail -5

    echo "[step 3/7] Seeding memory collections..."
    run_py -m memory.seed_data --domain "$domain" --db-path ./data/chromadb 2>&1 | tail -15

    # Start tools
    echo "[step 4/7] Starting ${domain} tool servers..."
    run_py -m domains.${domain}.tools.start_all &
    PIDS+=($!)
    sleep 3
    wait_for_health "http://localhost:${TOOL_BASE_PORT}/health" "${domain} tools" 30

    # Start MMA
    echo "[step 5/7] Starting MMA gateway..."
    run_py -m memory.mma_gateway --domain "$domain" --port $MMA_PORT &
    PIDS+=($!)
    wait_for_health "http://localhost:${MMA_PORT}/health" "MMA" 30 || true

    # Run benign E2E
    echo "[step 6/7] Running benign E2E tests..."
    echo ""

    mkdir -p "logs/${domain}_baseline_${GROUP}"

    for config in flat acl_hardened agenticcyops; do
        echo "  --- ${domain} / ${config} / Group ${GROUP} ---"
        run_py -c "
import asyncio, json, sys
sys.path.insert(0, '.')
from pathlib import Path
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
    group = '${GROUP}'
    llm_url = '${LLM_URL}'
    llm_provider = 'anthropic' if llm_url == 'anthropic' else 'openai'
    consensus_config = '${CONSENSUS_CONFIG}'

    logger = ExperimentLogger(
        eval_name='${domain}_baseline_${GROUP}',
        domain=domain,
        config=config,
        model='Group_${GROUP}',
    )
    logger.set_trial(ap='benign', variant=1, trial=1)

    enforcer = ManifestEnforcer(domain=domain, logger=logger)

    registry = ServerRegistry(domain=domain, logger=logger)
    registry.load_tools()
    port = ${TOOL_BASE_PORT}
    for tool_id in sorted(registry._servers.keys()):
        registry._ports[tool_id] = port
        port += 1

    all_schemas = registry.get_all_schemas()

    agents = {}
    for phase, AgentClass in [('monitor', MonitorAgent), ('analyze', AnalyzeAgent),
                               ('admin', AdminAgent), ('report', ReportAgent)]:
        manifest = enforcer.get_manifest(phase)
        phase_schemas = registry.get_phase_schemas(manifest.get('allowed_tools', []))
        agent_kwargs = dict(
            domain=domain,
            config=config,
            manifest=manifest,
            tool_schemas=phase_schemas,
            all_tool_schemas=all_schemas,
            logger=logger,
        )
        if llm_provider == 'anthropic':
            agent_kwargs['llm_provider'] = 'anthropic'
        else:
            agent_kwargs['llm_url'] = llm_url
        agents[phase] = AgentClass(**agent_kwargs)

    consensus = None
    if config == 'agenticcyops':
        try:
            from consensus.validator import ConsensusValidator
            consensus = ConsensusValidator(config_name=consensus_config, logger=logger)
            print(f'    Consensus: {consensus_config}')
        except Exception as e:
            print(f'    Consensus: skipped ({e})')

    host = SOARHost(
        domain=domain,
        config=config,
        llm_url=llm_url if llm_provider != 'anthropic' else 'http://localhost:8000/v1',
        tool_registry=registry,
        consensus=consensus,
        agents=agents,
        logger=logger,
    )

    # Load domain-appropriate benign incident
    _benign_file = Path(f'domains/{domain}/payloads/benign_alerts.json')
    if not _benign_file.exists():
        _benign_file = Path(f'domains/{domain}/payloads/benign_workflows.json')
    if _benign_file.exists():
        with open(_benign_file) as _f:
            _payloads = json.load(_f)
        incident = _payloads[0].get('trigger', _payloads[0])
        if 'incident_id' not in incident:
            incident['incident_id'] = f'{domain}-BENIGN-001'
    else:
        incident = {
            'incident_id': f'{domain}-BENIGN-001',
            'alert_type': 'generic_alert',
            'timestamp': '2026-04-09T10:00:00Z',
            'description': f'Benign test incident for {domain}.',
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

    # Verification + dashboard + report
    echo "[step 7/7] Generating verification report..."
    echo ""

    # Copy logs to standard location for verify_baseline compatibility
    mkdir -p "logs/${domain}_baseline"
    cp logs/${domain}_baseline_${GROUP}/*.jsonl "logs/${domain}_baseline/" 2>/dev/null || true

    run_py -m analysis.verify_baseline --domain "$domain" --config all 2>&1

    echo ""
    echo "Generating dashboard + report..."
    mkdir -p "${RESULT_DIR}/${domain}"
    run_py -m analysis.baseline_dashboard --domain "$domain" --output "${RESULT_DIR}/${domain}/" 2>&1 || true
    run_py -m analysis.generate_report --domain "$domain" --output "${RESULT_DIR}/${domain}/" 2>&1 || true

    # Clean up standard location
    rm -rf "logs/${domain}_baseline" 2>/dev/null || true

    echo ""
    echo "============================================================"
    echo "  ${domain} / Group ${GROUP} BASELINE COMPLETE"
    echo "  Results: ${RESULT_DIR}/${domain}/"
    echo "============================================================"

    # Stop domain services
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
for d in "${DOMAINS[@]}"; do
    run_domain_baseline "$d"
done

# Readiness gate
if [ ${#DOMAINS[@]} -gt 1 ]; then
    echo ""
    echo "============================================================"
    echo "  READINESS GATE — Group ${GROUP}"
    echo "============================================================"

    # Temporarily copy all group logs for verification
    for d in "${DOMAINS[@]}"; do
        mkdir -p "logs/${d}_baseline"
        cp logs/${d}_baseline_${GROUP}/*.jsonl "logs/${d}_baseline/" 2>/dev/null || true
    done

    run_py -m analysis.verify_baseline --domain all --config all 2>&1

    # Clean temp copies
    for d in "${DOMAINS[@]}"; do
        rm -rf "logs/${d}_baseline" 2>/dev/null || true
    done
fi

echo ""
echo "Done. Results in ${RESULT_DIR}/"
echo ""
echo "Results directory structure:"
find "${RESULT_DIR}" -type f 2>/dev/null | sort | head -30
