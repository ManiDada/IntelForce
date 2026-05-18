#!/usr/bin/env python3
"""Emit structured governance metadata for handoffs and reporting."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GOVERNANCE_FILE = ROOT / "data" / "queue-governance-state.json"


def main() -> int:
    if GOVERNANCE_FILE.exists():
        state = json.loads(GOVERNANCE_FILE.read_text())
    else:
        print("No governance state file found. Run queue_blocker_check.py first.")
        return 1

    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
