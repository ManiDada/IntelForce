#!/usr/bin/env bash
# Scaffold a delivery project for a won job.
# Usage: bash scripts/create_project.sh <job_id> [project_name]

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JOB_ID="${1:?Usage: create_project.sh <job_id> [project_name]}"
PROJECT_NAME="${2:-$JOB_ID}"
DEST="$ROOT/projects/$PROJECT_NAME"

if [[ -d "$DEST" ]]; then
  echo "Project already exists: $DEST"
  exit 1
fi

mkdir -p "$DEST"/{src,tests,docs,deliverables/screenshots}

cat > "$DEST/README.md" << EOF
# $PROJECT_NAME

## Setup
\`\`\`bash
cp .env.example .env
pip install -r requirements.txt
python src/main.py
\`\`\`

## Testing
\`\`\`bash
pytest tests/
\`\`\`
EOF

cat > "$DEST/.env.example" << 'EOF'
# Copy to .env and fill in values
# API_KEY=
# WEBHOOK_URL=
EOF

cat > "$DEST/src/main.py" << 'EOF'
#!/usr/bin/env python3
"""Entry point."""


def main():
    print("Running...")


if __name__ == "__main__":
    main()
EOF

cat > "$DEST/tests/test_main.py" << 'EOF'
"""Tests."""
from src.main import main


def test_main():
    main()
EOF

cat > "$DEST/deliverables/TEST-REPORT.md" << EOF
# Test Report: $PROJECT_NAME

Date: $(date +%Y-%m-%d)

## Test Results
- [ ] Unit tests: PASS
- [ ] Integration tests: PASS
- [ ] Edge cases tested: PASS

## Evidence
(Add screenshots / output logs here)
EOF

cat > "$DEST/delivery-notes.md" << EOF
# Delivery Notes: $PROJECT_NAME

Job ID: $JOB_ID
Created: $(date +%Y-%m-%d)

## Scope Summary
(What was delivered)

## Assumptions
(What was assumed)

## Handoff Notes
(What the client needs to know)
EOF

cat > "$DEST/requirements.txt" << 'EOF'
# Add project dependencies
requests>=2.31.0
python-dotenv>=1.0.0
EOF

echo "✅ Project scaffolded: $DEST"
echo "Next steps:"
echo "  1. Read the proposal from proposals/sent/ — every promise = acceptance criterion"
echo "  2. Fill in delivery-notes.md scope summary"
echo "  3. Build in src/, test in tests/"
echo "  4. Complete deliverables/TEST-REPORT.md before handoff"
