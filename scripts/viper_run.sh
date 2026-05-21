#!/usr/bin/env bash
# Viper's complete scan-score-notify pipeline.
# Runs every 8 minutes during day mode, 15 minutes at night.
# Called by Harry's viper-scan cron.

set -euo pipefail
ROOT="/Users/manidada/IntelForce"
cd "$ROOT"
LOG="$ROOT/logs/viper_$(date +%Y-%m-%d).log"
mkdir -p "$ROOT/logs"

echo "[$(date -u +%H:%M:%S)] VIPER RUN START" >> "$LOG"

# Check if cookies need refresh
if [[ -f "$ROOT/data/cookie_refresh_needed.flag" ]]; then
  echo "[$(date -u +%H:%M:%S)] ⚠️  Cookie refresh needed — skipping scan" >> "$LOG"
  exit 0
fi

# Step 1: Playwright scan
echo "[$(date -u +%H:%M:%S)] Starting Playwright scanner..." >> "$LOG"
python3 scanners/upwork_playwright_scanner.py >> "$LOG" 2>&1

# Step 2: Score and notify
echo "[$(date -u +%H:%M:%S)] Scoring and notifying..." >> "$LOG"
python3 scripts/score_and_notify.py --limit 5 >> "$LOG" 2>&1

# Step 3: Trigger Wordsmith for GO decisions
echo "[$(date -u +%H:%M:%S)] Triggering Wordsmith for proposals..." >> "$LOG"
python3 scripts/trigger_wordsmith.py >> "$LOG" 2>&1

echo "[$(date -u +%H:%M:%S)] VIPER RUN COMPLETE" >> "$LOG"
