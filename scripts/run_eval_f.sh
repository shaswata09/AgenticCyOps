#!/bin/bash
# ============================================================
# AgenticCyOps — Eval F: Multi-Domain Attack Evaluation
#
# Interactive or CLI. Runs domain-specific attack paths across
# Healthcare, Finance, Legal. Zero code changes — only --domain differs.
#
# Usage:
#   ./scripts/run_eval_f.sh                    # Interactive
#   ./scripts/run_eval_f.sh 10                 # All 3 domains, 10 trials
#   ./scripts/run_eval_f.sh 2 healthcare       # Single domain
# ============================================================

set -eE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONDA_ENV="agenticcyops"
TOOL_BASE_PORT=9000
MMA_PORT=9100
PIDS=()

ALL_DOMAINS=("healthcare" "finance" "legal")
DOMAIN_LABELS=("Healthcare (13 tools, AP-1/2/4)" "Finance (13 tools, AP-1/2/5)" "Legal (13 tools, AP-1/2/4)")

# ---- Interactive selection (if no arguments) ----
if [ -z "$1" ]; then
    echo ""
    echo "  AgenticCyOps — Eval F: Multi-Domain Evaluation"
    echo "  ──────────────────────────────────────────────"
    echo ""
    read -p "  Trials per variant [2]: " input_trials
    TRIALS="${input_trials:-2}"
    echo ""
    echo "  Domains:"
    echo "    1) healthcare  (13 tools, AP-1/2/4)"
    echo "    2) finance     (13 tools, AP-1/2/5)"
    echo "    3) legal       (13 tools, AP-1/2/4)"
    echo "    4) all (1-3)"
    echo "    q) quit"
    echo ""
    read -p "  Select domains (e.g. 1 2, or 4 for all): " choices

    if [[ "$choices" == "q" ]]; then
        echo "  Cancelled."
        exit 0
    fi

    SELECTED_DOMAINS=()
    for c in $choices; do
        case "$c" in
            1) SELECTED_DOMAINS+=("healthcare") ;;
            2) SELECTED_DOMAINS+=("finance") ;;
            3) SELECTED_DOMAINS+=("legal") ;;
            4) SELECTED_DOMAINS=("healthcare" "finance" "legal"); break ;;
        esac
    done
    [ ${#SELECTED_DOMAINS[@]} -eq 0 ] && echo "  No domains selected." && exit 0

else
    TRIALS="${1:-2}"
    if [ "${2:-all}" = "all" ]; then
        SELECTED_DOMAINS=("${ALL_DOMAINS[@]}")
    else
        SELECTED_DOMAINS=("$2")
    fi
fi

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
echo "  AgenticCyOps — Eval F: Multi-Domain Evaluation"
echo "  Trials per variant: ${TRIALS}"
echo "  Domains: ${SELECTED_DOMAINS[*]}"
echo "============================================================"

# Check vLLM
if ! curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: vLLM Primary not running. Start with: ./start_servers.sh"
    exit 1
fi
echo "[  ok] vLLM Primary (8000)"

START_TIME=$(date +%s)

run_domain() {
    local domain="$1"
    echo ""
    echo "============================================================"
    echo "  Domain: ${domain}"
    echo "============================================================"

    # Clean ports
    for port in $(seq ${TOOL_BASE_PORT} $((TOOL_BASE_PORT + 15))) ${MMA_PORT}; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
    done
    sleep 1
    PIDS=()

    # Setup ChromaDB
    echo "[1/5] ChromaDB setup..."
    run_py -m memory.chromadb_setup --domain "$domain" --db-path ./data/chromadb 2>&1 | tail -2
    run_py -m memory.seed_data --domain "$domain" --db-path ./data/chromadb 2>&1 | tail -2

    # Start tools
    echo "[2/5] Starting ${domain} tools..."
    run_py -m domains.${domain}.tools.start_all &
    PIDS+=($!)
    sleep 3
    wait_for_health "http://localhost:${TOOL_BASE_PORT}/health" "${domain} tools" 30

    # Start MMA
    echo "[3/5] Starting MMA..."
    run_py -m memory.mma_gateway --domain "$domain" --port $MMA_PORT &
    PIDS+=($!)
    wait_for_health "http://localhost:${MMA_PORT}/health" "MMA" 30 || true

    # Determine which APs this domain has
    local payload_dir="domains/${domain}/payloads"
    local ap_files=$(ls ${payload_dir}/ap*_variants.json 2>/dev/null || true)

    # Run attacks
    echo "[4/5] Running attacks..."
    for config in flat acl_hardened agenticcyops; do
        echo "  --- ${domain} / ${config} ---"

        for ap_file in $ap_files; do
            ap=$(basename "$ap_file" _variants.json)
            echo "    ${ap} (${TRIALS} trials/variant)..."
            run_py -m attacks.harness \
                --domain "$domain" --ap "$ap" --config "$config" \
                --trials "$TRIALS" --tool-port $TOOL_BASE_PORT \
                --verbose 2>&1 | grep -E "v[0-9]+ t[0-9]+|Error" || true
        done

        echo "    benign..."
        run_py -m attacks.harness \
            --domain "$domain" --benign --config "$config" \
            --trials 5 --tool-port $TOOL_BASE_PORT \
            2>&1 | grep -E "benign|Error" || true
    done

    # Baseline verification
    echo "[5/5] Verification..."
    run_py -m analysis.verify_baseline --domain "$domain" --config all 2>&1 || true

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

# Run selected domains
for domain in "${SELECTED_DOMAINS[@]}"; do
    run_domain "$domain"
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# Generate cross-domain analysis
echo ""
echo "============================================================"
echo "  Generating Cross-Domain Analysis"
echo "============================================================"

mkdir -p results/eval_f

run_py -c "
import json, sys, csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, '.')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

sns.set_theme(style='whitegrid', font_scale=1.0, palette='muted')

CONFIGS = ['flat', 'acl_hardened', 'agenticcyops']
CONFIG_LABELS = {'flat': 'Flat MAS', 'acl_hardened': 'ACL-Hardened', 'agenticcyops': 'AgenticCyOps'}
CONFIG_COLORS = {'flat': '#e74c3c', 'acl_hardened': '#f39c12', 'agenticcyops': '#2ecc71'}
DOMAIN_COLORS = {'cyberops': '#3498db', 'healthcare': '#e74c3c', 'finance': '#f39c12', 'legal': '#9b59b6'}
HEADER_COLOR = '#2c3e50'

# Collect trials from ALL domains
log_dir = Path('logs')
trials = []
for f in sorted(log_dir.rglob('*.jsonl')):
    with open(f) as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            e = json.loads(line)
            if e.get('action') == 'trial_complete':
                trials.append(e)

if not trials:
    print('No trial results found')
    sys.exit(0)

# Save CSV
csv_path = 'results/eval_f/cross_domain_results.csv'
with open(csv_path, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Domain', 'AP', 'Variant', 'Trial', 'Config', 'Succeeded', 'Mechanism'])
    for t in trials:
        w.writerow([t.get('domain',''), t.get('ap',''), t.get('variant',''),
                     t.get('trial',''), t.get('config',''),
                     t.get('attack_succeeded', False), t.get('blocking_mechanism','')])
print(f'Saved: {csv_path} ({len(trials)} trials)')

# Compute per-domain per-config ASR
domains = sorted(set(t.get('domain','') for t in trials))
attack_trials = [t for t in trials if t.get('ap','').startswith('ap')]

# R10 table
print()
print('=' * 80)
print('R10: CROSS-DOMAIN ATTACK INTERCEPTION')
print('=' * 80)

# Group by AP pattern across domains
ap_patterns = defaultdict(lambda: defaultdict(list))
for t in attack_trials:
    ap = t.get('ap', '')[:3]  # ap1, ap2, etc.
    domain = t.get('domain', '')
    config = t.get('config', '')
    ap_patterns[(ap, config)][domain].append(t.get('attack_succeeded', False))

# Chart: Cross-domain ASR comparison
fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)
fig.suptitle('R10: Cross-Domain Attack Interception', fontsize=16, fontweight='bold')

for ax, config in zip(axes, CONFIGS):
    domain_data = defaultdict(lambda: defaultdict(list))
    for t in attack_trials:
        if t.get('config') == config:
            ap = t.get('ap', '')
            domain = t.get('domain', '')
            domain_data[ap][domain].append(t.get('attack_succeeded', False))

    aps = sorted(set(t.get('ap','') for t in attack_trials))
    x = np.arange(len(domains))
    width = 0.15

    for i, ap in enumerate(aps[:6]):
        vals = []
        for domain in domains:
            results = domain_data.get(ap, {}).get(domain, [])
            if results:
                asr = sum(1 for r in results if r) / len(results) * 100
            else:
                asr = 0
            vals.append(asr)
        ax.bar(x + i * width, vals, width, label=ap, alpha=0.8)

    ax.set_title(CONFIG_LABELS.get(config, config), fontsize=12, fontweight='bold')
    ax.set_xticks(x + width * 2.5)
    ax.set_xticklabels([d.title() for d in domains], fontsize=9)
    ax.set_ylabel('ASR (%)' if config == 'flat' else '')
    ax.set_ylim(0, 110)
    if config == 'flat':
        ax.legend(fontsize=7, title='AP', ncol=2)
    sns.despine(ax=ax)

plt.tight_layout()
plt.savefig('results/eval_f/cross_domain_asr.png', dpi=150)
plt.close()
print('Saved: results/eval_f/cross_domain_asr.png')

# PDF Report
with PdfPages('results/eval_f/eval_f_report.pdf') as pdf:
    # Title
    fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis('off')
    ax.text(0.5, 0.7, 'AgenticCyOps', transform=ax.transAxes,
            ha='center', fontsize=36, fontweight='bold', color=HEADER_COLOR)
    ax.text(0.5, 0.6, 'Evaluation F: Multi-Domain Generalizability', transform=ax.transAxes,
            ha='center', fontsize=20, color='#7f8c8d')
    ax.text(0.5, 0.5, f'{len(trials)} trials across {len(domains)} domains',
            transform=ax.transAxes, ha='center', fontsize=14, color='#2980b9')
    ax.text(0.5, 0.42, 'Zero Framework Code Changes Across Domains',
            transform=ax.transAxes, ha='center', fontsize=14, fontweight='bold', color='#27ae60')
    ax.plot([0.2, 0.8], [0.47, 0.47], transform=ax.transAxes, color='#2980b9', linewidth=2)
    ax.text(0.5, 0.3, datetime.now().strftime('%B %d, %Y'), transform=ax.transAxes,
            ha='center', fontsize=12, color='#95a5a6')
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

    # R10 Table
    fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis('off')
    ax.set_title('R10: Cross-Domain Attack Interception', fontsize=18, fontweight='bold',
                 color=HEADER_COLOR, pad=30)

    headers = ['Domain'] + [CONFIG_LABELS[c] for c in CONFIGS] + ['Code Changes']
    cell_data = []
    for domain in domains:
        row = [domain.title()]
        for config in CONFIGS:
            dt = [t for t in attack_trials if t.get('domain') == domain and t.get('config') == config]
            if dt:
                blocked = sum(1 for t in dt if not t.get('attack_succeeded', False))
                row.append(f'{blocked}/{len(dt)} blocked')
            else:
                row.append('--')
        row.append('0')
        cell_data.append(row)

    table = ax.table(cellText=cell_data, colLabels=headers, cellLoc='center',
                     loc='center', bbox=[0.05, 0.15, 0.9, 0.65])
    table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1, 2.2)
    for j in range(len(headers)):
        table[0, j].set_facecolor(HEADER_COLOR)
        table[0, j].set_text_props(color='white', fontweight='bold')
    for i in range(1, len(cell_data) + 1):
        table[i, len(headers)-1].set_facecolor('#eafaf1')
        table[i, len(headers)-1].set_text_props(fontweight='bold', color='#27ae60')
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

    # Cross-domain chart
    img = plt.imread('results/eval_f/cross_domain_asr.png')
    fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis('off'); ax.imshow(img)
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

    # Summary
    fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis('off')
    ax.set_title('Key Finding: Zero Code Changes', fontsize=18, fontweight='bold',
                 color=HEADER_COLOR, pad=30)
    y = 0.8
    for domain in domains:
        dt = [t for t in attack_trials if t.get('domain') == domain and t.get('config') == 'agenticcyops']
        if dt:
            blocked = sum(1 for t in dt if not t.get('attack_succeeded', False))
            rate = blocked / len(dt) * 100
            ax.text(0.08, y, f'{domain.title()}: {rate:.0f}% interception rate ({blocked}/{len(dt)} blocked)',
                    transform=ax.transAxes, fontsize=14, color=DOMAIN_COLORS.get(domain, '#2c3e50'),
                    fontweight='bold')
            y -= 0.08

    ax.text(0.08, y - 0.05,
            'The same Host, consensus module, and MMA gateway code deployed across\\n'
            'all domains with zero modification. Only JSON configs and tool stubs differ.',
            transform=ax.transAxes, fontsize=12, color='#7f8c8d')
    ax.text(0.5, 0.05, datetime.now().strftime('%Y-%m-%d %H:%M'), transform=ax.transAxes,
            ha='center', fontsize=10, color='#bdc3c7')
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

print('Saved: results/eval_f/eval_f_report.pdf')
" 2>&1

echo ""
echo "============================================================"
echo "  Eval F COMPLETE"
echo "  Results: results/eval_f/"
echo "  Time: ${ELAPSED}s ($((ELAPSED / 60))m)"
echo "============================================================"
