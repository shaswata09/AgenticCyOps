#!/bin/bash
# ============================================================
# Pre-commit guard: no absolute repo paths, no credentials.
#
# The repo is published, so this runs over everything a commit would
# actually add -- which is the part an earlier version of this check got
# wrong. `git status --porcelain` collapses an untracked DIRECTORY into a
# single entry, so filtering its output through `[ -f "$f" ]` silently
# skipped every file inside a new results/ or logs/ directory. Using
# `-uall` expands those directories to individual files.
# ============================================================
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

# The absolute path of this checkout, derived here so it is never written
# into the repository itself.
ABS="$(pwd -P)"
fail=0

# Every path a commit would touch: staged, modified, and untracked --
# with -uall so untracked directories are expanded to their files.
mapfile -t files < <(git status --porcelain -uall | cut -c4- | sed 's/^"//; s/"$//')
[ "${#files[@]}" -eq 0 ] && { echo "[  ok] nothing to check"; exit 0; }

# Run records (logs, per-trial results) are kept byte-identical to what the
# runs wrote, absolute paths included, and are scrubbed only when the release
# snapshot is built (scripts/build_snapshot.sh). The path check therefore skips
# them; the secret check below still covers them.
is_run_record() {
    case "$1" in
        logs/*|logs_legacy_v1/*|results_legacy_v1/*|results/eval_attacks/*) return 0 ;;
        *) return 1 ;;
    esac
}

check() {  # check <label> <skip-run-records:0|1> <grep-args...>
    local label="$1" skip_records="$2"; shift 2
    local hits=()
    for f in "${files[@]}"; do
        [ -f "$f" ] || continue
        [ "$skip_records" = 1 ] && is_run_record "$f" && continue
        grep -Iq "$@" -- "$f" 2>/dev/null && hits+=("$f")
    done
    if [ "${#hits[@]}" -gt 0 ]; then
        echo "[FAIL] $label in ${#hits[@]} file(s):"
        printf '         %s\n' "${hits[@]:0:10}"
        [ "${#hits[@]}" -gt 10 ] && echo "         ... and $(( ${#hits[@]} - 10 )) more"
        fail=1
    else
        echo "[  ok] no $label"
    fi
}

check "absolute repo paths" 1 -F "$ABS"
check "API-key-shaped strings" 0 -E -e 'sk-[A-Za-z0-9]{20,}' -e 'ghp_[A-Za-z0-9]{20,}' \
                                  -e 'AKIA[0-9A-Z]{16}' -e 'Bearer [A-Za-z0-9._-]{20,}'

# .env must never be committed, whatever it contains.
if git status --porcelain -uall | cut -c4- | grep -qx '.env'; then
    echo "[FAIL] .env is staged or untracked-and-would-be-added"
    fail=1
else
    echo "[  ok] .env not in the commit"
fi

[ "$fail" -eq 0 ] && echo "[  ok] path/secret guard passed"
exit "$fail"
