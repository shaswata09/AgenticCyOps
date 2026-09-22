#!/bin/bash
# Snapshot of the external-review programme's progress.
#
#   ./scripts/programme_status.sh          # one snapshot
#   ./scripts/programme_status.sh watch    # append a snapshot every 10 min
#                                          # until the driver exits
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

APS_RE='"ap(2|3|9|13|14)"'

MARK="logs/programme_start.txt"
# Only count trials written by THIS programme: the log dirs already hold the
# previous run's files, so restrict to jsonl newer than the start marker.
newfiles() { # newfiles <dir> [nameglob]
    [ -f "$MARK" ] || { echo ""; return; }
    find "$1" -maxdepth 1 -name "${2:-*.jsonl}" -newer "$MARK" 2>/dev/null
}
ntrials() { # ntrials <dir> [nameglob]
    local fs; fs=$(newfiles "$1" "${2:-*.jsonl}")
    [ -z "$fs" ] && { echo 0; return; }
    cat $fs 2>/dev/null | grep '"trial_complete"' | grep -Ec "$APS_RE" || echo 0
}

snapshot() {
    echo "================ $(date '+%F %T') ================"
    if pgrep -f run_review_programme.sh >/dev/null; then
        echo "driver: RUNNING   streams: $(pgrep -cf 'run_attack_paths.sh' 2>/dev/null || echo 0)"
    else
        echo "driver: not running"
    fi

    local total=0
    echo "-- E5.5 q235_div4 main (target 300/config, T=3) --"
    for cfg in flat acl_hardened symbolic_only agenticcyops llm_judge; do
        local n=0
        for d in cyberops finance healthcare legal; do
            local c; c=$(ntrials "logs/${d}_eval_attacks_q235_div4" "${cfg}_*.jsonl")
            n=$((n + ${c:-0}))
        done
        total=$((total+n))
        printf "   %-15s %4d / 300\n" "$cfg" "$n"
    done

    echo "-- E5.5 ablations (target 75/arm, T=3) --"
    for p in P1 P2 P3 P4 P5; do
        local c; c=$(ntrials "logs/cyberops_eval_attacks_q235_div4_disabled_${p}")
        total=$((total + ${c:-0}))
        printf "   minus %-9s %4d / 75\n" "$p" "${c:-0}"
    done

    echo "-- E5.5 transfer (T=2) --"
    for g in llama8b_div4 scout_div4 mistral_div3p; do
        local n=0
        for d in cyberops finance; do
            local c; c=$(ntrials "logs/${d}_eval_attacks_${g}")
            n=$((n + ${c:-0}))
        done
        total=$((total+n))
        printf "   %-15s %4d / 150\n" "$g" "$n"
    done

    echo "-- E4.2 ASB frozen full run (target 1530) --"
    local asb; asb=$(find results/asb -name results.csv -newermt '-14 hours' 2>/dev/null \
        | xargs -r wc -l 2>/dev/null | tail -1 | awk '{print $1}')
    printf "   rows: %s\n" "${asb:-0}"
    tail -2 logs/prog_asb_e42.log 2>/dev/null | sed 's/^/   /'

    echo "-- GPU --"
    nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader 2>/dev/null | sed 's/^/   /'
    echo "attack trials complete so far: $total"
    echo
}

case "${1:-once}" in
    watch)
        while true; do
            snapshot >> logs/programme_status.log 2>&1
            pgrep -f run_review_programme.sh >/dev/null || {
                echo "$(date '+%F %T')  driver finished -- status watch exiting" \
                    >> logs/programme_status.log
                break
            }
            sleep 600
        done
        ;;
    *) snapshot ;;
esac
