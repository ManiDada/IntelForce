#!/bin/bash
set -e
cd /Users/manidada/IntelForce
echo "Tue May 19 12:44:59 UTC 2026 poll start" >> data/poll.log
SERPER_API_KEY=4189103f6a1e9cd4f6991af912b07f2d46c60b46 python3 /Users/manidada/IntelForce/scripts/serper_job_search.py
python3 scripts/revenue_pipeline.py --no-dry-run --gate-mode manual --limit 50
python3 scripts/notify_scored_jobs.py
echo "Tue May 19 12:44:59 UTC 2026 poll done" >> data/poll.log
