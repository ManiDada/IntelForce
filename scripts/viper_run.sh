#!/usr/bin/env bash
# Viper's complete scan-score-notify pipeline.
# Uses curl_cffi GraphQL scanner with Chrome TLS fingerprint.
# No Playwright. No cookies file. No browser needed.
# Runs every 8 minutes during day mode, 15 minutes at night.

set -euo pipefail
ROOT="/Users/manidada/IntelForce"
cd "$ROOT"
LOG="$ROOT/logs/viper_$(date +%Y-%m-%d).log"
mkdir -p "$ROOT/logs"

ts() { date -u +"%H:%M:%S"; }

echo "[$(ts)] VIPER RUN START" >> "$LOG"

# Step 1: GQL discovery (no enrichment until upwork-mcp Chrome session set up)
echo "[$(ts)] GQL scan (title filter, no enrichment)..." >> "$LOG"
python3 -m scanners.upwork_graphql_scanner --no-enrich --limit 30 >> "$LOG" 2>&1
EXIT=$?

if [[ $EXIT -ne 0 ]]; then
  echo "[$(ts)] Scanner failed (exit $EXIT)" >> "$LOG"
  exit $EXIT
fi

# Step 2: Score and notify Mads via Telegram
echo "[$(ts)] Scoring + notifying..." >> "$LOG"
python3 scripts/score_and_notify.py --limit 5 >> "$LOG" 2>&1

# Step 3: Trigger Wordsmith for GO decisions
echo "[$(ts)] Triggering Wordsmith..." >> "$LOG"
python3 scripts/trigger_wordsmith.py >> "$LOG" 2>&1

echo "[$(ts)] VIPER RUN COMPLETE" >> "$LOG"
