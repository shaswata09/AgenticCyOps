#!/bin/bash
# ============================================================
# AgenticCyOps — Eval A: CyberOps Attack Path Replay
#
# Interactive or CLI. Runs APs × variants × trials × configs + benign.
# Generates: CSV, ASR chart, heatmap, PDF report.
#
# Usage:
#   ./scripts/run_eval_a.sh                # Interactive
#   ./scripts/run_eval_a.sh 6              # 6 trials, all APs, all configs
#   ./scripts/run_eval_a.sh 2 ap1          # Quick: 2 trials, AP-1 only
#   ./scripts/run_eval_a.sh 6 ap1 agenticcyops  # Single AP + config
# ============================================================

set -eE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONDA_ENV="agenticcyops"
TOOL_BASE_PORT=9000
MMA_PORT=9100
DOMAIN="cyberops"
PIDS=()

ALL_APS=("ap1" "ap2" "ap3" "ap4" "ap5" "ap6")
AP_NAMES=("AP-1 Tool Redirection" "AP-2 Memory Poisoning" "AP-3 Confused Deputy" "AP-4 Cross-Phase Exfil" "AP-5 Irreversible Action" "AP-6 Replay Attack")
ALL_CONFIGS=("flat" "acl_hardened" "agenticcyops")

# ---- Interactive selection (if no arguments) ----
if [ -z "$1" ]; then
    clear
    echo ""
    echo "  AgenticCyOps — Eval A: CyberOps Attack Paths"
    echo "  ──────────────────────────────────────────────"
    echo ""

    echo ""
    echo "  AgenticCyOps — Eval A: CyberOps Attack Paths"
    echo "  ──────────────────────────────────────────────"
    echo ""
    read -p "  Trials per variant [6]: " input_trials
    TRIALS="${input_trials:-6}"
    echo ""
    echo "  Attack Paths:"
    echo "    1) ap1  Tool Redirection"
    echo "    2) ap2  Memory Poisoning"
    echo "    3) ap3  Confused Deputy"
    echo "    4) ap4  Cross-Phase Exfiltration"
    echo "    5) ap5  Irreversible Action"
    echo "    6) ap6  Replay Attack"
    echo "    7) all (1-6)"
    echo ""
    read -p "  Select APs (e.g. 1 2 3, or 7 for all): " ap_choices

    SELECTED_APS=()
    for c in $ap_choices; do
        case "$c" in
            1) SELECTED_APS+=("ap1") ;; 2) SELECTED_APS+=("ap2") ;;
            3) SELECTED_APS+=("ap3") ;; 4) SELECTED_APS+=("ap4") ;;
            5) SELECTED_APS+=("ap5") ;; 6) SELECTED_APS+=("ap6") ;;
            7) SELECTED_APS=("ap1" "ap2" "ap3" "ap4" "ap5" "ap6"); break ;;
        esac
    done
    [ ${#SELECTED_APS[@]} -eq 0 ] && echo "  No APs selected." && exit 0

    echo ""
    echo "  Configs:"
    echo "    1) flat"
    echo "    2) acl_hardened"
    echo "    3) agenticcyops"
    echo "    4) all (1-3)"
    echo ""
    read -p "  Select configs (e.g. 1 3, or 4 for all): " cfg_choices

    SELECTED_CONFIGS=()
    for c in $cfg_choices; do
        case "$c" in
            1) SELECTED_CONFIGS+=("flat") ;;
            2) SELECTED_CONFIGS+=("acl_hardened") ;;
            3) SELECTED_CONFIGS+=("agenticcyops") ;;
            4) SELECTED_CONFIGS=("flat" "acl_hardened" "agenticcyops"); break ;;
        esac
    done
    [ ${#SELECTED_CONFIGS[@]} -eq 0 ] && echo "  No configs selected." && exit 0
else
    TRIALS="${1:-6}"
    AP_FILTER="${2:-all}"
    CONFIG_FILTER="${3:-all}"

    if [ "$AP_FILTER" = "all" ]; then
        SELECTED_APS=("${ALL_APS[@]}")
    else
        SELECTED_APS=("$AP_FILTER")
    fi

    if [ "$CONFIG_FILTER" = "all" ]; then
        SELECTED_CONFIGS=("${ALL_CONFIGS[@]}")
    else
        SELECTED_CONFIGS=("$CONFIG_FILTER")
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
echo "  AgenticCyOps — Eval A: CyberOps Attack Paths"
echo "  Trials per variant: ${TRIALS}"
echo "  APs: ${SELECTED_APS[*]}"
echo "  Configs: ${SELECTED_CONFIGS[*]}"
echo "============================================================"

# ---- Step 0: Clean stale ports ----
echo ""
echo "[step 0/6] Cleaning stale ports..."
for port in $(seq ${TOOL_BASE_PORT} $((TOOL_BASE_PORT + 15))) ${MMA_PORT}; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
done
sleep 1

# ---- Step 1: Check vLLM ----
echo ""
echo "[step 1/6] Checking vLLM servers..."
if ! curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: vLLM Primary not running. Start with: ./start_servers.sh"
    exit 1
fi
echo "[  ok] Primary (8000)"
for port in 8002 8005; do
    curl -s --max-time 2 http://localhost:$port/health > /dev/null 2>&1 && echo "[  ok] Validator ($port)" || echo "[ warn] Validator ($port) not running"
done

# ---- Step 2: Setup ChromaDB + seed ----
echo ""
echo "[step 2/6] Initializing ChromaDB..."
run_py -m memory.chromadb_setup --domain $DOMAIN --db-path ./data/chromadb 2>&1 | tail -3
echo "Seeding..."
run_py -m memory.seed_data --domain $DOMAIN --db-path ./data/chromadb 2>&1 | tail -3

# ---- Step 3: Start tool servers ----
echo ""
echo "[step 3/6] Starting tool servers..."
run_py -m domains.${DOMAIN}.tools.start_all &
PIDS+=($!)
sleep 3
wait_for_health "http://localhost:${TOOL_BASE_PORT}/health" "tools" 30

# ---- Step 4: Start MMA gateway ----
echo ""
echo "[step 4/6] Starting MMA gateway..."
run_py -m memory.mma_gateway --domain $DOMAIN --port $MMA_PORT &
PIDS+=($!)
wait_for_health "http://localhost:${MMA_PORT}/health" "MMA" 30 || true

# ---- Step 5: Run attack trials ----
echo ""
echo "[step 5/6] Running attack trials..."
echo ""

START_TIME=$(date +%s)

for config in "${SELECTED_CONFIGS[@]}"; do
    echo "=== Config: $config ==="

    for ap in "${SELECTED_APS[@]}"; do
        echo "  Running $ap ($TRIALS trials/variant)..."
        run_py -m attacks.harness \
            --domain $DOMAIN --ap $ap --config $config \
            --trials $TRIALS --tool-port $TOOL_BASE_PORT \
            --verbose 2>&1 | grep -E "v[0-9]+ t[0-9]+|Error|SUMMARY" || true
        echo ""
    done

    echo "  Running benign (20 scenarios)..."
    run_py -m attacks.harness \
        --domain $DOMAIN --benign --config $config \
        --trials 20 --tool-port $TOOL_BASE_PORT \
        2>&1 | grep -E "benign|Error|SUMMARY" || true
    echo ""
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo ""
echo "Attack trials completed in $((ELAPSED / 60))m $((ELAPSED % 60))s"

# ---- Step 6: Generate analysis ----
echo ""
echo "[step 6/6] Generating analysis..."
echo ""

mkdir -p results/eval_a

run_py -c "
import json, sys, csv
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '.')
log_dir = Path('logs')

# Collect all trial_complete events
trials = []
for f in sorted(log_dir.rglob('*.jsonl')):
    if 'eval_a' not in str(f) and 'cyberops' not in str(f):
        continue
    with open(f) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get('action') == 'trial_complete':
                trials.append(e)

if not trials:
    print('No trial results found in logs/')
    sys.exit(0)

# Build summary CSV
csv_path = 'results/eval_a/attack_results.csv'
with open(csv_path, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['AP', 'Variant', 'Trial', 'Config', 'Succeeded', 'Interception_Step', 'Mechanism'])
    for t in trials:
        w.writerow([
            t.get('ap', ''),
            t.get('variant', ''),
            t.get('trial', ''),
            t.get('config', ''),
            t.get('attack_succeeded', ''),
            t.get('interception_step', ''),
            t.get('blocking_mechanism', ''),
        ])
print(f'Saved: {csv_path} ({len(trials)} trials)')

# Compute ASR per AP per config
print()
print('=' * 70)
print('ATTACK SUCCESS RATE (ASR) SUMMARY')
print('=' * 70)
print(f'{\"AP\":<10} {\"Config\":<18} {\"Total\":<8} {\"Succeeded\":<11} {\"ASR\":<8}')
print('-' * 55)

groups = defaultdict(list)
for t in trials:
    ap = t.get('ap', 'unknown')
    config = t.get('config', 'unknown')
    groups[(ap, config)].append(t.get('attack_succeeded', False))

for (ap, config), results in sorted(groups.items()):
    total = len(results)
    succeeded = sum(1 for r in results if r)
    asr = f'{succeeded/total*100:.0f}%' if total else 'N/A'
    print(f'{ap:<10} {config:<18} {total:<8} {succeeded:<11} {asr:<8}')

# R1 table: Attack Interception
print()
print('=' * 70)
print('R1: ATTACK INTERCEPTION BY CONFIGURATION')
print('=' * 70)

aps = sorted(set(t.get('ap', '') for t in trials if t.get('ap', '').startswith('ap')))
configs = ['flat', 'acl_hardened', 'agenticcyops']

print(f'{\"AP\":<10}', end='')
for c in configs:
    print(f'{c:<18}', end='')
print()
print('-' * 64)

for ap in aps:
    print(f'{ap:<10}', end='')
    for c in configs:
        key = (ap, c)
        if key in groups:
            total = len(groups[key])
            blocked = sum(1 for r in groups[key] if not r)
            print(f'{blocked}/{total} blocked{\"\":>4}', end='')
        else:
            print(f'{\"--\":<18}', end='')
    print()
" 2>&1

# Generate charts
echo ""
echo "Generating charts..."
run_py -c "
import json, sys, csv
from pathlib import Path
from collections import defaultdict

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

# Load results
csv_path = 'results/eval_a/attack_results.csv'
if not Path(csv_path).exists():
    print('No results CSV')
    sys.exit(0)

trials = []
with open(csv_path) as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['Succeeded'] = row['Succeeded'] == 'True'
        trials.append(row)

if not trials:
    print('No data')
    sys.exit(0)

# Compute ASR per AP per config
aps = sorted(set(t['AP'] for t in trials if t['AP'].startswith('ap')))
asr_data = {}
for ap in aps:
    for config in CONFIGS:
        matching = [t for t in trials if t['AP'] == ap and t['Config'] == config]
        if matching:
            total = len(matching)
            succeeded = sum(1 for t in matching if t['Succeeded'])
            asr_data[(ap, config)] = succeeded / total * 100

# ---- Chart 1: ASR by AP by Config ----
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(aps))
width = 0.25

for i, config in enumerate(CONFIGS):
    vals = [asr_data.get((ap, config), 0) for ap in aps]
    bars = ax.bar(x + i * width, vals, width,
                  label=CONFIG_LABELS.get(config, config),
                  color=CONFIG_COLORS.get(config, '#95a5a6'),
                  edgecolor='white', linewidth=1.5)
    for bar, val in zip(bars, vals):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{val:.0f}%', ha='center', va='bottom', fontsize=8, fontweight='bold')

ax.set_xticks(x + width)
ap_labels = {'ap1': 'AP-1\nTool Redir.', 'ap2': 'AP-2\nMem Poison', 'ap3': 'AP-3\nConfused Dep.',
             'ap4': 'AP-4\nCross-Phase', 'ap5': 'AP-5\nIrreversible', 'ap6': 'AP-6\nReplay'}
ax.set_xticklabels([ap_labels.get(ap, ap) for ap in aps])
ax.set_ylabel('Attack Success Rate (%)')
ax.set_title('R1: Attack Success Rate by Configuration', fontsize=14, fontweight='bold')
ax.set_ylim(0, 110)
ax.legend(title='Configuration', frameon=True)
ax.axhline(y=0, color='black', linewidth=0.5)
sns.despine(ax=ax)
plt.tight_layout()
plt.savefig('results/eval_a/asr_by_ap.png', dpi=150)
plt.close()
print('Saved: results/eval_a/asr_by_ap.png')

# ---- Chart 2: Interception heatmap ----
matrix = np.zeros((len(aps), len(CONFIGS)))
for i, ap in enumerate(aps):
    for j, config in enumerate(CONFIGS):
        matching = [t for t in trials if t['AP'] == ap and t['Config'] == config]
        if matching:
            blocked = sum(1 for t in matching if not t['Succeeded'])
            matrix[i, j] = blocked / len(matching) * 100

fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(matrix, annot=True, fmt='.0f', cmap='RdYlGn',
            xticklabels=[CONFIG_LABELS.get(c, c) for c in CONFIGS],
            yticklabels=[ap_labels.get(ap, ap) for ap in aps],
            vmin=0, vmax=100, linewidths=1, linecolor='white',
            cbar_kws={'label': 'Interception Rate (%)'}, ax=ax)
ax.set_title('Attack Interception Rate (%)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('results/eval_a/interception_heatmap.png', dpi=150)
plt.close()
print('Saved: results/eval_a/interception_heatmap.png')

# ---- PDF Report ----
from datetime import datetime
HEADER_COLOR = '#2c3e50'

with PdfPages('results/eval_a/eval_a_report.pdf') as pdf:
    # Title page
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis('off')
    ax.text(0.5, 0.7, 'AgenticCyOps', transform=ax.transAxes,
            ha='center', fontsize=36, fontweight='bold', color=HEADER_COLOR)
    ax.text(0.5, 0.6, 'Evaluation A: CyberOps Attack Path Replay', transform=ax.transAxes,
            ha='center', fontsize=20, color='#7f8c8d')
    ax.text(0.5, 0.5, f'${len(trials)} trials across {len(aps)} attack paths x 3 configs',
            transform=ax.transAxes, ha='center', fontsize=14, color='#2980b9')
    ax.text(0.5, 0.4, datetime.now().strftime('%B %d, %Y %H:%M'), transform=ax.transAxes,
            ha='center', fontsize=12, color='#95a5a6')
    ax.plot([0.2, 0.8], [0.47, 0.47], transform=ax.transAxes, color='#2980b9', linewidth=2)
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

    # R1 Table
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis('off')
    ax.set_title('R1: Attack Interception Results', fontsize=18, fontweight='bold',
                 color=HEADER_COLOR, pad=30)
    headers = ['Attack Path', 'Flat MAS', 'ACL-Hardened', 'AgenticCyOps']
    cell_data = []
    for ap in aps:
        row = [ap_labels.get(ap, ap).replace(chr(10), ' ')]
        for config in CONFIGS:
            matching = [t for t in trials if t['AP'] == ap and t['Config'] == config]
            if matching:
                total = len(matching)
                succeeded = sum(1 for t in matching if t['Succeeded'])
                blocked = total - succeeded
                asr = succeeded / total * 100
                row.append(f'{blocked}/{total} blocked ({asr:.0f}% ASR)')
            else:
                row.append('--')
        cell_data.append(row)

    table = ax.table(cellText=cell_data, colLabels=headers, cellLoc='center',
                     loc='center', bbox=[0.05, 0.1, 0.9, 0.75])
    table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1, 2.2)
    for j in range(len(headers)):
        table[0, j].set_facecolor(HEADER_COLOR)
        table[0, j].set_text_props(color='white', fontweight='bold')
    for i in range(1, len(cell_data) + 1):
        table[i, 0].set_text_props(fontweight='bold')
        table[i, 1].set_facecolor('#fdedec')
        table[i, 2].set_facecolor('#fef9e7')
        table[i, 3].set_facecolor('#eafaf1')
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

    # ASR chart
    img = plt.imread('results/eval_a/asr_by_ap.png')
    fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis('off')
    ax.imshow(img)
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

    # Heatmap
    img = plt.imread('results/eval_a/interception_heatmap.png')
    fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis('off')
    ax.imshow(img)
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

    # Summary
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis('off')
    ax.set_title('Key Findings', fontsize=18, fontweight='bold', color=HEADER_COLOR, pad=30)

    total_trials = len(trials)
    attack_trials = [t for t in trials if t['AP'].startswith('ap')]
    benign_trials = [t for t in trials if t['AP'] == 'benign']

    # Per-config summary
    y = 0.8
    for config in CONFIGS:
        ct = [t for t in attack_trials if t['Config'] == config]
        if ct:
            succeeded = sum(1 for t in ct if t['Succeeded'])
            blocked = len(ct) - succeeded
            asr = succeeded / len(ct) * 100
            color = CONFIG_COLORS.get(config, '#2c3e50')
            ax.text(0.08, y, f'{CONFIG_LABELS.get(config, config)}: {asr:.0f}% ASR ({succeeded}/{len(ct)} attacks succeeded, {blocked} blocked)',
                    transform=ax.transAxes, fontsize=13, color=color, fontweight='bold')
            y -= 0.07

    y -= 0.05
    ax.text(0.08, y, f'Total trials: {total_trials} ({len(attack_trials)} attack + {len(benign_trials)} benign)',
            transform=ax.transAxes, fontsize=12, color='#7f8c8d')
    y -= 0.05
    ax.text(0.08, y, f'Trials per variant: ${TRIALS}',
            transform=ax.transAxes, fontsize=12, color='#7f8c8d')

    ax.text(0.5, 0.05, datetime.now().strftime('%Y-%m-%d %H:%M'), transform=ax.transAxes,
            ha='center', fontsize=10, color='#bdc3c7')
    pdf.savefig(fig, bbox_inches='tight'); plt.close()

print('Saved: results/eval_a/eval_a_report.pdf')
" 2>&1

echo ""
echo "============================================================"
echo "  Eval A COMPLETE"
echo "  Results: results/eval_a/"
echo "    attack_results.csv"
echo "    asr_by_ap.png"
echo "    interception_heatmap.png"
echo "    eval_a_report.pdf"
echo "  Time: ${ELAPSED}s"
echo "============================================================"
