#!/bin/bash
# ============================================================
# AgenticCyOps — Autonomous Baseline Runner
#
# Sequentially starts servers for each model group (A-F),
# runs baseline for all 4 domains, then shuts down servers
# before moving to the next group. Fully unattended.
#
# Usage:
#   ./scripts/run_autonomous_baseline.sh              # All groups A-F
#   ./scripts/run_autonomous_baseline.sh A C F         # Specific groups
#   ./scripts/run_autonomous_baseline.sh --skip-existing  # Skip groups with results
#
# Estimated time: ~30-45 min per group (4 domains × 3 configs)
# Total: ~3-4.5 hours for all 6 groups
# ============================================================

set -eE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONDA_ENV="agenticcyops"
MODELS_DIR="$(pwd)/models"
LOG_DIR="$(pwd)/logs/vllm"
mkdir -p "$LOG_DIR"

ALL_GROUPS=("A" "B" "C" "D" "E" "F")
ALL_DOMAINS=("cyberops" "healthcare" "finance" "legal")
SKIP_EXISTING=false

# ---- Parse args ----
SELECTED_GROUPS=()
for arg in "$@"; do
    case "$arg" in
        --skip-existing) SKIP_EXISTING=true ;;
        [A-F]) SELECTED_GROUPS+=("$arg") ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done
[ ${#SELECTED_GROUPS[@]} -eq 0 ] && SELECTED_GROUPS=("${ALL_GROUPS[@]}")

# ---- Server definitions (same as start_servers.sh) ----
declare -A SRV_NAME SRV_PORT SRV_GPU SRV_CMD
SRV_NAME[0]="Qwen3-235B";        SRV_PORT[0]=8000; SRV_GPU[0]="0,1,4,5"
SRV_NAME[1]="GLM-4.7-FP8";       SRV_PORT[1]=8001; SRV_GPU[1]="0,1,4,5"
SRV_NAME[2]="Qwen3-32B (V1)";    SRV_PORT[2]=8002; SRV_GPU[2]="2"
SRV_NAME[3]="DeepSeek-R1 (V2)";  SRV_PORT[3]=8005; SRV_GPU[3]="3"
SRV_NAME[4]="Mistral (V5)";      SRV_PORT[4]=8003; SRV_GPU[4]="3"
SRV_NAME[5]="Llama-4-Scout (V3)"; SRV_PORT[5]=8004; SRV_GPU[5]="4,5"

SRV_CMD[0]="vllm serve $MODELS_DIR/Qwen/Qwen3-235B-A22B-Instruct-2507 --tensor-parallel-size 4 --dtype bfloat16 --enable-auto-tool-choice --tool-call-parser hermes --gpu-memory-utilization 0.9 --max-model-len 32768 --enforce-eager --port 8000"
SRV_CMD[1]="vllm serve $MODELS_DIR/zai-org/GLM-4.7-FP8 --tensor-parallel-size 4 --dtype auto --enable-auto-tool-choice --tool-call-parser glm47 --reasoning-parser glm45 --gpu-memory-utilization 0.9 --max-model-len 32768 --enforce-eager --port 8001"
SRV_CMD[2]="vllm serve $MODELS_DIR/Qwen/Qwen3-32B --dtype bfloat16 --gpu-memory-utilization 0.9 --max-model-len 32768 --port 8002"
SRV_CMD[3]="vllm serve $MODELS_DIR/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B --dtype bfloat16 --gpu-memory-utilization 0.9 --max-model-len 32768 --port 8005"
SRV_CMD[4]="vllm serve $MODELS_DIR/mistralai/Mistral-Small-3.2-24B-Instruct-2506 --dtype bfloat16 --tokenizer-mode mistral --gpu-memory-utilization 0.9 --max-model-len 32768 --port 8003"
SRV_CMD[5]="vllm serve $MODELS_DIR/meta-llama/Llama-4-Scout-17B-16E-Instruct --tensor-parallel-size 2 --dtype bfloat16 --enable-auto-tool-choice --tool-call-parser llama4_pythonic --gpu-memory-utilization 0.9 --max-model-len 32768 --enforce-eager --port 8004"

# Group compositions (indices into SRV_* arrays)
declare -A GROUP_IDX
GROUP_IDX[A]="0 2 3"    # Qwen3-235B + V1 + V2
GROUP_IDX[B]="1 2 3"    # GLM-4.7 + V1 + V2
GROUP_IDX[C]="0 2"      # Qwen3-235B + V1 (same-family)
GROUP_IDX[D]="5 2 3"    # Llama-4-Scout + V1 + V2
GROUP_IDX[E]="0 2 4"    # Qwen3-235B + V1 + V5(Mistral)
GROUP_IDX[F]="2 3 5"    # Claude primary — V1 + V2 + V3

# ---- Helpers ----
run_py() { conda run --no-capture-output -n "$CONDA_ENV" python3 "$@"; }

log() { echo "[$(date '+%H:%M:%S')] $*"; }

kill_all_vllm() {
    log "Killing all vLLM processes..."
    pkill -f "vllm serve" 2>/dev/null || true
    sleep 3
    # Force kill any remaining
    pkill -9 -f "vllm serve" 2>/dev/null || true
    sleep 2
    log "All vLLM processes stopped."
}

wait_for_server() {
    local port=$1 name=$2 timeout=${3:-300} elapsed=0
    while ! curl -s --max-time 2 "http://localhost:$port/health" > /dev/null 2>&1; do
        sleep 5; elapsed=$((elapsed + 5))
        if [ $elapsed -ge $timeout ]; then
            log "TIMEOUT: $name (port $port) did not start in ${timeout}s"
            return 1
        fi
        if [ $((elapsed % 30)) -eq 0 ]; then
            log "  Waiting for $name (port $port)... ${elapsed}s"
        fi
    done
    log "  $name (port $port) ready (${elapsed}s)"
    return 0
}

start_group_servers() {
    local group=$1
    local indices=(${GROUP_IDX[$group]})

    log "Starting servers for Group $group..."

    # Disable FlashInfer (H200 CUTLASS JIT issue)
    local FLASHINFER_DIR
    FLASHINFER_DIR=$(python3 -c "import flashinfer; import os; print(os.path.dirname(flashinfer.__file__))" 2>/dev/null || true)
    if [ -n "$FLASHINFER_DIR" ] && [ -d "$FLASHINFER_DIR" ] && [ ! -d "${FLASHINFER_DIR}_disabled" ]; then
        mv "$FLASHINFER_DIR" "${FLASHINFER_DIR}_disabled"
        log "  Disabled FlashInfer (CUTLASS JIT broken on H200)"
    fi
    export VLLM_ATTENTION_BACKEND=FLASH_ATTN
    rm -rf ~/.cache/flashinfer 2>/dev/null || true

    # Launch servers sequentially to avoid OOM
    for idx in "${indices[@]}"; do
        local port=${SRV_PORT[$idx]}
        local name=${SRV_NAME[$idx]}
        local gpu=${SRV_GPU[$idx]}
        local cmd=${SRV_CMD[$idx]}
        local logfile="$LOG_DIR/port_${port}.log"

        # Kill any existing process on this port
        local existing_pid
        existing_pid=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$existing_pid" ]; then
            kill -9 $existing_pid 2>/dev/null || true
            sleep 2
        fi

        > "$logfile"
        log "  Launching $name on GPU $gpu → port $port"
        CUDA_VISIBLE_DEVICES="$gpu" $cmd > "$logfile" 2>&1 &

        # Wait a bit between launches to avoid GPU memory contention
        sleep 10
    done

    # Wait for all servers to be healthy
    log "Waiting for all Group $group servers to be ready..."
    local all_up=true
    for idx in "${indices[@]}"; do
        if ! wait_for_server "${SRV_PORT[$idx]}" "${SRV_NAME[$idx]}" 600; then
            all_up=false
        fi
    done

    if [ "$all_up" = false ]; then
        log "ERROR: Not all servers started for Group $group"
        return 1
    fi

    log "All Group $group servers ready."
    return 0
}

stop_group_servers() {
    local group=$1
    local indices=(${GROUP_IDX[$group]})

    log "Stopping Group $group servers..."
    for idx in "${indices[@]}"; do
        local port=${SRV_PORT[$idx]}
        local pid
        pid=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    sleep 5
    # Force kill any remaining
    for idx in "${indices[@]}"; do
        local port=${SRV_PORT[$idx]}
        local pid
        pid=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    sleep 3
    log "Group $group servers stopped."
}

# ---- Cleanup trap ----
cleanup() {
    echo ""
    log "Interrupted — killing all servers..."
    kill_all_vllm
    # Kill tool/MMA processes
    for port in $(seq 9000 9015) 9100; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
    done
    exit 1
}
trap cleanup SIGINT SIGTERM

# ---- Main ----
TOTAL_START=$(date +%s)
RESULTS_SUMMARY=()

echo ""
echo "============================================================"
echo "  AgenticCyOps — Autonomous Baseline Runner"
echo "============================================================"
echo ""
echo "  Groups: ${SELECTED_GROUPS[*]}"
echo "  Domains: ${ALL_DOMAINS[*]}"
echo "  Configs: flat, acl_hardened, agenticcyops"
echo "  Skip existing: $SKIP_EXISTING"
echo ""

for group in "${SELECTED_GROUPS[@]}"; do
    GROUP_START=$(date +%s)

    echo ""
    echo "============================================================"
    echo "  GROUP $group"
    echo "============================================================"

    # Check if results already exist
    if [ "$SKIP_EXISTING" = true ]; then
        all_exist=true
        for domain in "${ALL_DOMAINS[@]}"; do
            if [ ! -d "results/baseline/group_${group}/${domain}" ]; then
                all_exist=false
                break
            fi
        done
        if [ "$all_exist" = true ]; then
            log "SKIP: Group $group — results already exist"
            RESULTS_SUMMARY+=("Group $group: SKIPPED (existing)")
            continue
        fi
    fi

    # Kill any stale vLLM processes before starting
    kill_all_vllm

    # Start servers for this group
    if ! start_group_servers "$group"; then
        log "FAILED to start Group $group servers — skipping"
        RESULTS_SUMMARY+=("Group $group: FAILED (servers)")
        stop_group_servers "$group"
        continue
    fi

    # Run baseline for all domains
    log "Running baseline for Group $group — all domains..."
    if bash scripts/run_baseline.sh "$group" 5; then
        log "Group $group baseline COMPLETED"
        RESULTS_SUMMARY+=("Group $group: COMPLETED")
    else
        log "Group $group baseline FAILED"
        RESULTS_SUMMARY+=("Group $group: FAILED (baseline)")
    fi

    # Stop servers for this group
    stop_group_servers "$group"

    GROUP_END=$(date +%s)
    GROUP_ELAPSED=$((GROUP_END - GROUP_START))
    log "Group $group total time: $((GROUP_ELAPSED / 60))m $((GROUP_ELAPSED % 60))s"
done

# ---- Summary ----
TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_END - TOTAL_START))

echo ""
echo "============================================================"
echo "  AUTONOMOUS BASELINE — COMPLETE"
echo "============================================================"
echo ""
for result in "${RESULTS_SUMMARY[@]}"; do
    echo "  $result"
done
echo ""
echo "  Total time: $((TOTAL_ELAPSED / 60))m $((TOTAL_ELAPSED % 60))s"
echo ""

# Run verification across all completed groups
log "Running verification across all groups..."
run_py -m analysis.verify_baseline --domain all --config all 2>&1 || true

echo ""
echo "============================================================"
echo "  DONE"
echo "============================================================"
