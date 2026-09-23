#!/bin/bash
# ============================================================
# Third-review queue: waits for the running E2 sweep, then runs the
# configuration-variant arms in priority order.
#
#   E16 agenticcyops_gate_permissive   what deterministic approval costs (W1/Q1)
#   E17 p2_judge                       P2 + panel, isolating the rest (W2/Q4)
#   E1  agenticcyops_noautoapprove     judge-everything-after-rules (concern 1)
#
# Each arm is the development split (CyberOps, all APs, 3 trials) plus the 20
# CyberOps benign scenarios x 3 -- 285 incidents per arm. All three run
# concurrently as 6 streams, which is well inside the envelope that stayed
# stable yesterday (12 without panels, 9 with; 13 with panels crashed the
# primary).
# ============================================================
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
[ -f .env ] && { set -a; . ./.env; set +a; }

STATUS="logs/third_review_queue.log"
GROUP="q235_div4"
export SKIP_REPORT=1 OMP_NUM_THREADS="${OMP_NUM_THREADS:-6}"
note() { echo "$(date '+%F %T')  $*" | tee -a "$STATUS"; }

# ---- 1. wait for the E2 sweep to drain ----
note "waiting for the E2 sweep to finish"
while pgrep -f "run_attack_paths.sh ${GROUP}" >/dev/null 2>&1; do sleep 120; done
note "E2 finished"

# ---- 2. gates: clean tree, freeze, live servers ----
if ! bash scripts/check_freeze.sh >>"$STATUS" 2>&1; then
    note "ABORT: freeze guard failed"; exit 1
fi
dirty=$(/home/student/.conda/envs/agenticcyops/bin/python -c \
        "from logging_utils.run_metadata import git_state; print(git_state()['git_dirty'])")
if [ "$dirty" != "False" ]; then note "ABORT: tree is dirty ($dirty)"; exit 1; fi
for p in 8000 8002 8003; do
    curl -s --max-time 20 "http://127.0.0.1:${p}/health" >/dev/null 2>&1 \
        || { note "ABORT: :$p not answering"; exit 1; }
done
note "gates passed (freeze v2.5, clean tree, servers up)"

date -Iseconds > logs/third_review_start.txt

# ---- 3. run the three arms concurrently ----
slot=0; pids=()
for cfg in agenticcyops_gate_permissive p2_judge agenticcyops_noautoapprove; do
    for aps in all benign; do
        note "start ${cfg} cyberops ${aps} (slot ${slot})"
        SLOT="$slot" TRIALS=3 \
            scripts/run_attack_paths.sh "$GROUP" cyberops "$aps" "$cfg" 3 \
            > "logs/tr_${cfg}_${aps}.log" 2>&1 &
        pids+=($!); slot=$((slot + 1)); sleep 25
    done
done
for p in "${pids[@]}"; do wait "$p"; done
note "all three arms finished"

/home/student/.conda/envs/agenticcyops/bin/python -m analysis.parse_logs >/dev/null 2>&1 || true
note "parse complete -- queue done"
