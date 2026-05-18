#!/usr/bin/env python3
"""CLI entry point for the revenue pipeline.

Usage:
    python3 scripts/revenue_pipeline.py --dry-run --gate-mode manual --limit 20
    JOBS_JSON_PATH=/tmp/test-jobs.json python3 scripts/revenue_pipeline.py --dry-run
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.runner import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="IntelForce revenue pipeline runner")
    parser.add_argument("--config", help="Path to config JSON (overrides other flags)")
    parser.add_argument("--limit", type=int, default=20, help="Max jobs to process")
    parser.add_argument(
        "--gate-mode",
        choices=["manual", "auto_high_conf"],
        default="manual",
        help="manual = always queue for review | auto_high_conf = auto-send if EV≥82 + confidence≥85",
    )
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Don't write files or update DB (default: True)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                        help="Actually write proposals and update DB")
    parser.add_argument("--allow-send", action="store_true", default=False,
                        help="Allow auto-send (requires gate-mode=auto_high_conf)")
    args = parser.parse_args()

    cfg: dict = {}
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))

    result = run_pipeline(
        limit=cfg.get("limit", args.limit),
        gate_mode=cfg.get("gate_mode", args.gate_mode),
        dry_run=cfg.get("dry_run", args.dry_run),
        allow_send=cfg.get("allow_send", args.allow_send),
    )

    print(json.dumps(result, indent=2))

    processed = result["processed"]
    proposals = result["proposals_generated"]
    held = result["held"]
    print(f"\n✅ Processed {processed} jobs → {proposals} proposals generated, {held} held")
    if result["dry_run"]:
        print("⚠️  DRY RUN — no files written, no DB changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
