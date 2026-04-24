#!/bin/bash
# ============================================================
# AgenticCyOps — InjecAgent GCG (adaptive) adversarial-suffix generation
#
# Runs white-box Greedy-Coordinate-Gradient search against one
# downloaded primary / validator model and saves a per-case
# adversarial suffix under:
#
#     benchmarks/injecagent/adaptive/strings/<model_alias>/<case_id>.json
#
# These suffixes can then be applied during the live-LLM end-to-end
# sweep via `scripts/run_injecagent_e2e.sh --adaptive <model_alias>`.
#
# Requirements: the target model's GPUs must be FREE (no vLLM worker
# running on them).  GCG needs HuggingFace-level gradient access,
# which vLLM's inference path does not expose.
#
# Usage:
#   ./scripts/run_injecagent_adaptive_gen.sh                      # Interactive
#   ./scripts/run_injecagent_adaptive_gen.sh llama4               # Full 50-case sweep
#   ./scripts/run_injecagent_adaptive_gen.sh llama4 500 64 bf16   # Tune GCG hyperparams
#   ./scripts/run_injecagent_adaptive_gen.sh llama4 500 64 bf16 3 # Smoke: first 3 cases
# ============================================================

set -eE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONDA_ENV="agenticcyops"

# ---- Supported target models (must match TARGET_MODELS in gcg_runner.py) ----
declare -A MODEL_DESC
MODEL_DESC[llama4]="Llama-4-Scout-17B-16E-Instruct  (Group D primary, fits on 1 H200)"
MODEL_DESC[qwen235]="Qwen3-235B-A22B-Instruct-2507   (Groups A/C/E primary, needs all 6 H200s)"
MODEL_DESC[qwen32]="Qwen3-32B                         (Validator V1, ~64 GB with gradients)"
MODEL_DESC[mistral]="Mistral-Small-3.2-24B-Instruct-2506 (Validator V5)"

ALL_MODELS=(llama4 qwen235 qwen32 mistral)

run_py() { conda run --no-capture-output -n "$CONDA_ENV" python3 "$@"; }

# ---- CLI / interactive ----
if [ -z "$1" ]; then
    echo ""
    echo "  AgenticCyOps — InjecAgent Adaptive (GCG) Suffix Generation"
    echo "  ──────────────────────────────────────────────────────────"
    echo ""
    echo "  Target models:"
    for m in "${ALL_MODELS[@]}"; do
        printf "    %-10s %s\n" "$m" "${MODEL_DESC[$m]}"
    done
    echo ""
    read -p "  Target model: " MODEL
    read -p "  GCG steps [default 500]: " STEPS
    read -p "  Batch / search width [default 64]: " BATCH
    read -p "  Dtype [bf16 / fp16 / fp32, default bf16]: " DTYPE
    read -p "  Case limit [leave blank for full 50]: " CASE_LIMIT
else
    MODEL="${1}"
    STEPS="${2:-500}"
    BATCH="${3:-64}"
    DTYPE="${4:-bf16}"
    CASE_LIMIT="${5:-}"
fi

[ -z "$STEPS" ] && STEPS=500
[ -z "$BATCH" ] && BATCH=64
[ -z "$DTYPE" ] && DTYPE="bf16"

case " ${ALL_MODELS[*]} " in
    *" $MODEL "*) ;;
    *) echo "[FAIL] unknown model: '$MODEL'. Choose one of: ${ALL_MODELS[*]}"; exit 2 ;;
esac

# ---- Precondition: representative subset must exist ----
SUBSET="benchmarks/injecagent/adaptive/representative_cases.json"
if [ ! -f "$SUBSET" ]; then
    echo "[prep] Generating representative 50-case subset..."
    run_py -m benchmarks.injecagent.adaptive.representative_subset
fi

# ---- Precondition: GPU availability ----
echo ""
echo "[preflight] GPU memory check"
USED_MIB=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{s+=$1} END {print s}')
AVAIL_MIB=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | awk '{s+=$1} END {print s}')
echo "    total used: $((USED_MIB/1024)) GiB    free: $((AVAIL_MIB/1024)) GiB"
if [ "$AVAIL_MIB" -lt 40000 ] && [ "$MODEL" != "qwen32" ] && [ "$MODEL" != "mistral" ]; then
    echo ""
    echo "[WARN] Less than 40 GiB free across GPUs.  GCG against $MODEL may OOM."
    echo "       Consider stopping vLLM workers first:"
    echo "         ps aux | grep vllm   # find PIDs"
    echo "         kill <pid>"
    read -p "Continue anyway? [y/N]: " ans
    [[ "$ans" != "y" && "$ans" != "Y" ]] && exit 3
fi

# ---- Run ----
echo ""
echo "  Target model:  $MODEL  (${MODEL_DESC[$MODEL]})"
echo "  GCG steps:     $STEPS"
echo "  Batch / width: $BATCH"
echo "  Dtype:         $DTYPE"
[ -n "$CASE_LIMIT" ] && echo "  Case limit:    $CASE_LIMIT"
echo ""
echo "  Output dir:    benchmarks/injecagent/adaptive/strings/$MODEL/"
echo ""

ARGS=(--model "$MODEL" --steps "$STEPS" --batch-size "$BATCH" --dtype "$DTYPE")
[ -n "$CASE_LIMIT" ] && ARGS+=(--case-limit "$CASE_LIMIT")

echo "[run] python -m benchmarks.injecagent.adaptive.gcg_runner ${ARGS[*]}"
echo ""
run_py -m benchmarks.injecagent.adaptive.gcg_runner "${ARGS[@]}"

echo ""
echo "[done] Adversarial suffixes saved."
echo "       Next step -- run adaptive e2e for a group:"
echo "           ./scripts/run_injecagent_e2e.sh <GROUP> all 6 all '' $MODEL"
