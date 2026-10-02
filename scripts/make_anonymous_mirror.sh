#!/bin/bash
# ============================================================
# Build the anonymous artifact for double-blind review.
#
#   scripts/make_anonymous_mirror.sh [OUT_DIR]      (default: ../defer-anonymous)
#
# Exports the committed tree (git archive HEAD, so nothing untracked and no
# .git), drops what must not be shared (legacy outputs, the paper source,
# secrets, notebooks with outputs), and then refuses to finish if anything
# identifying remains: author names or e-mail, home or checkout paths, internal
# addresses given in ANON_EXTRA_PATTERNS, API-key-shaped strings. Extra patterns can be passed in
# ANON_EXTRA_PATTERNS (a grep -E alternation), e.g. an institution name.
# ============================================================
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
OUT="${1:-../defer-anonymous}"
[ -e "$OUT" ] && { echo "[FAIL] $OUT exists; remove it or pass another directory"; exit 1; }
mkdir -p "$OUT"

git archive --format=tar HEAD | tar -x -C "$OUT"
rm -rf "$OUT"/logs_legacy_v1 "$OUT"/results_legacy_v1 "$OUT"/paper/main.tex \
       "$OUT"/paper/camera_ready_authors.tex "$OUT"/.env "$OUT"/models/test_scripts \
       "$OUT"/REVIEW_READY_TASKS.md "$OUT"/docs/REVISION_TASKS.md
find "$OUT" -name "*.ipynb" -path "*existing_defense_eval*" -delete 2>/dev/null || true

# the public repository names its authors (citation block, CITATION.cff, its URL,
# read from the git remote); the review copy drops them, and this script
rm -f "$OUT"/CITATION.cff "$OUT"/scripts/make_anonymous_mirror.sh
repo_url="$(git remote get-url origin 2>/dev/null | sed -E 's#^git@([^:]+):#https://\1/#; s#\.git$##' || true)"
python3 - "$OUT" "$repo_url" <<'PY'
import pathlib, re, sys
out, url = pathlib.Path(sys.argv[1]), sys.argv[2]
readme = out / "README.md"
s = readme.read_text()
s = re.sub(r"\n## Citation\n.*?(?=\n## )", "\n", s, flags=re.S)
s = s.replace("- [Citation](#citation)\n", "")
s = re.sub(r",?\s*see \[Citation\]\(#citation\)", "", s)
if url:
    s = re.sub(r"\s*Code: <" + re.escape(url) + r">\.", "", s)
readme.write_text(s)
if url:
    for f in out.rglob("*"):
        if f.is_file() and f.suffix in {".md", ".py", ".sh", ".txt", ".yaml", ".html", ".tex", ".cff"}:
            t = f.read_text(errors="ignore")
            if url in t:
                f.write_text(t.replace(url, "(repository link withheld for review)"))
PY

# identity of whoever builds the mirror, read from git config, never written here
name="$(git config user.name || true)"; email="$(git config user.email || true)"
user_pat=""
for w in $name; do [ ${#w} -ge 4 ] && user_pat="${user_pat:+$user_pat|}\\b$w\\b"; done   # whole words
# the e-mail's local part only: a public provider's domain (e.g. a webmail
# service) also appears in the synthetic scenarios
[ -n "$email" ] && user_pat="${user_pat:+$user_pat|}${email%%@*}"
# (the scenarios use synthetic 10.0.x.x addresses throughout, so real network
# prefixes are passed in ANON_EXTRA_PATTERNS rather than matched generically)
pats="/home/[a-z][a-z0-9_-]+/|/storage/data|/Users/[A-Za-z]|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}"
[ -n "$user_pat" ] && pats="$pats|$user_pat"
# the repository owner, from the remote URL
owner="$(echo "$repo_url" | sed -E 's#^https?://[^/]+/([^/]+)/.*#\1#')"
[ -n "$owner" ] && [ "$owner" != "$repo_url" ] && pats="$pats|\\b$owner\\b"
[ -n "${ANON_EXTRA_PATTERNS:-}" ] && pats="$pats|$ANON_EXTRA_PATTERNS"

# synthetic scenario paths in payloads and logs (e.g. /home/auser/...) are not
# identifying; list them here so the gate can tell them apart
allow="/home/(auser|user|helpdesk|programs)/"
hits=$(grep -rIEil "$pats" "$OUT" | while read -r f; do
          if grep -IEi "$pats" "$f" | grep -vEq "$allow"; then echo "$f"; fi
       done || true)
if [ -n "$hits" ]; then
    echo "[FAIL] identifying strings remain in $(echo "$hits" | wc -l) file(s):"
    echo "$hits" | head -20 | sed 's/^/         /'
    exit 1
fi
echo "[  ok] anonymous mirror at $OUT ($(du -sh "$OUT" | cut -f1)); no identifying strings found"
