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

ABS="/storage/data/AgenticCyOps"
fail=0

# Every path a commit would touch: staged, modified, and untracked --
# with -uall so untracked directories are expanded to their files.
mapfile -t files < <(git status --porcelain -uall | cut -c4- | sed 's/^"//; s/"$//')
[ "${#files[@]}" -eq 0 ] && { echo "[  ok] nothing to check"; exit 0; }

# These two define the pattern, so they are the one place it may appear.
is_exempt() {
    case "$1" in
        scripts/check_paths.sh|scripts/scrub_paths.py) return 0 ;;
        *) return 1 ;;
    esac
}

check() {  # check <label> <grep-args...>
    local label="$1"; shift
    local hits=()
    for f in "${files[@]}"; do
        [ -f "$f" ] || continue
        is_exempt "$f" && continue
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

check "absolute repo paths"  -F "$ABS"
check "API-key-shaped strings" -E -e 'sk-[A-Za-z0-9]{20,}' -e 'ghp_[A-Za-z0-9]{20,}' \
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
