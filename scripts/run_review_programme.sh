#!/bin/bash
# ============================================================
# External-review programme, sized to a ~10 hour budget.
#
# Measured per-stream throughput on this box (trials/hour/stream):
#   flat 92.5 | acl_hardened 94.0 | symbolic_only 67.2
#   agenticcyops 44.5 | llm_judge 20.1
# llm_judge is the long pole, so it starts first and everything else is
# scheduled around it.
#
# Trial counts (reduced from the task block to fit the budget):
#   E5.5 q235 main + ablations   3 trials  (headline comparison, unchanged)
#   E5.5 transfer groups         2 trials  (was 3)
#   E4.2 ASB frozen full run     2 trials  (was 5; all 255 cases x 3 configs kept,
#                                          coverage is what the abstract needs)
#
#   ./scripts/run_review_programme.sh            # everything
#   ./scripts/run_review_programme.sh a1         # one phase
# ============================================================
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

[ -f .env ] && { set -a; . ./.env; set +a; }

STATUS="logs/programme_status.log"
APS="ap2,ap3,ap9,ap13,ap14"
GROUP="q235_div4"
SMALL_EMB="$PWD/models/Qwen/Qwen3-Embedding-0.6B"
export SKIP_REPORT=1 OMP_NUM_THREADS="${OMP_NUM_THREADS:-6}"

note() { echo "$(date '+%F %T')  $*" | tee -a "$STATUS"; }

# emb model: flat / acl / judge-only arms use the small embedder like the
# previous programme did, so the store behaves the same across arms.
emb_for() { case "$1" in flat|acl_hardened|llm_judge) echo "$SMALL_EMB" ;; *) echo "" ;; esac; }

# one stream = one (group, domain, config) attack run
stream() { # stream <slot> <group> <domain> <config> <trials> [tagsuffix]
    local slot="$1" g="$2" dom="$3" cfg="$4" tr="$5" sfx="${6:-}"
    SLOT="$slot" MMA_MODEL_PATH="$(emb_for "$cfg")" TRIALS="$tr" \
        scripts/run_attack_paths.sh "$g" "$dom" "$APS" "$cfg" "$tr" \
        > "logs/prog_${g}_${dom}_${cfg}${sfx}.log" 2>&1
}

ablation() { # ablation <slot> <principle>
    local slot="$1" p="$2"
    SLOT="$slot" DISABLE_PRINCIPLES="$p" TRIALS=3 \
        scripts/run_attack_paths.sh "$GROUP" cyberops "$APS" agenticcyops 3 \
        > "logs/prog_ablation_${p}.log" 2>&1
}

DOMAINS=(cyberops finance healthcare legal)

# ---------------------------------------------------------------- A0
# Llama-3.1-8B lives on the RTX 5090 node, so it costs the H200 box nothing
# and runs alongside everything else.
a0_llama8b() {
    local code; code=$(curl -s -o /dev/null --max-time 5 \
        -H "Authorization: Bearer ${REMOTE_5090_API_KEY:-}" \
        -w "%{http_code}" "${REMOTE_5090_URL:-http://127.0.0.1:1}/models" 2>/dev/null || echo 000)
    if [ "$code" != "200" ]; then note "A0 skip: A51 unreachable (HTTP $code)"; return 0; fi
    note "A0 start: llama8b_div4 cyberops+finance x 3 configs (T=2) on A51"
    local slot=0 pids=()
    for dom in cyberops finance; do
        for cfg in flat acl_hardened agenticcyops; do
            stream "$slot" llama8b_div4 "$dom" "$cfg" 2 & pids+=($!)
            slot=$((slot+1)); sleep 25
        done
    done
    for p in "${pids[@]}"; do wait "$p"; done
    note "A0 done: llama8b_div4"
}

# ---------------------------------------------------------------- A1
# Fast arms first: 12 streams, ~1.1 h.
a1_fast() {
    note "A1 start: q235 flat/acl/symbolic x 4 domains (T=3), 12 streams"
    local slot=0 pids=()
    for cfg in symbolic_only acl_hardened flat; do
        for dom in "${DOMAINS[@]}"; do
            stream "$slot" "$GROUP" "$dom" "$cfg" 3 & pids+=($!)
            slot=$((slot+1)); sleep 25
        done
    done
    for p in "${pids[@]}"; do wait "$p"; done
    note "A1 done"
}

# ---------------------------------------------------------------- A2
# Slow arms + ablations + the ASB full run, all concurrent. llm_judge is the
# long pole (~3.7 h on 4 streams) so the ASB run fits inside its shadow.
a2_slow() {
    note "A2 start: q235 judge+aco x 4 domains, 5 ablation arms, ASB full run"
    local slot=0 pids=()
    for cfg in llm_judge agenticcyops; do
        for dom in "${DOMAINS[@]}"; do
            stream "$slot" "$GROUP" "$dom" "$cfg" 3 & pids+=($!)
            slot=$((slot+1)); sleep 25
        done
    done
    for p in P1 P2 P3 P4 P5; do
        ablation "$slot" "$p" & pids+=($!)
        slot=$((slot+1)); sleep 25
    done
    ( note "A2 ASB: E4.2 frozen full run, 255 cases x 2 trials x 3 configs"
      scripts/run_asb_e2e.sh "$GROUP" all 2 all 3 > logs/prog_asb_e42.log 2>&1
      note "A2 ASB done" ) & pids+=($!)
    for p in "${pids[@]}"; do wait "$p"; done
    note "A2 done"
}

# ---------------------------------------------------------------- B
# Transfer groups need the mid profile, so the 235B has to come down first.
b_transfer() {
    note "B start: switching q235 -> mid profile"
    bash scripts/vllm_profiles.sh stop  > logs/prog_profile_stop.log 2>&1
    sleep 20
    bash scripts/vllm_profiles.sh start mid > logs/prog_profile_mid.log 2>&1
    local t0=$(date +%s)
    until curl -s --max-time 3 http://127.0.0.1:8004/health >/dev/null 2>&1; do
        [ $(( $(date +%s) - t0 )) -gt 2400 ] && { note "B FAIL: mid profile did not come up"; return 1; }
        sleep 20
    done
    note "B: mid profile up, launching scout + mistral (T=2)"
    local slot=0 pids=()
    for g in scout_div4 mistral_div3p; do
        for dom in cyberops finance; do
            for cfg in flat acl_hardened agenticcyops; do
                stream "$slot" "$g" "$dom" "$cfg" 2 & pids+=($!)
                slot=$((slot+1)); sleep 25
            done
        done
    done
    for p in "${pids[@]}"; do wait "$p"; done
    note "B done"
}

main() {
    date -Iseconds > logs/programme_start.txt
    note "===== review programme start (budget ~10 h) ====="
    bash scripts/check_freeze.sh | tee -a "$STATUS"
    a1_fast
    a2_slow
    # llama8b only needs the A51 endpoint, but its harness, MMA gateway and
    # tool servers still run here, so it waits until the 235B phases are done.
    a0_llama8b &
    local a0=$!
    b_transfer
    wait "$a0" 2>/dev/null
    note "===== review programme complete ====="
}

case "${1:-all}" in
    a0) a0_llama8b ;;
    a1) a1_fast ;;
    a2) a2_slow ;;
    b)  b_transfer ;;
    all) main ;;
    *) echo "usage: $0 [all|a0|a1|a2|b]"; exit 1 ;;
esac
