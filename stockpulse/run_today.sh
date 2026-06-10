#!/bin/bash
# StockPulse — daily report runner
# Usage: ./run_today.sh [TICKER]
# If no ticker, uses next stock from watchlist rotation

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== StockPulse $(date '+%Y-%m-%d %H:%M %Z') ==="

# Fetch data and generate report
if [ -n "$1" ]; then
  echo "Running for: $1"
  DATA=$(python3 "$SCRIPT_DIR/fetch_data.py" "$1" 2>/dev/null)
else
  echo "Running next stock in watchlist rotation..."
  DATA=$(python3 "$SCRIPT_DIR/fetch_data.py" 2>/dev/null)
fi

REPORT_PATH=$(echo "$DATA" | python3 "$SCRIPT_DIR/generate_report.py")
echo "Generated: $REPORT_PATH"

# Rebuild index
python3 "$SCRIPT_DIR/build_index.py"
echo "Index rebuilt."

# Git push
cd "$REPO_DIR"
git add stockpulse/
git commit -m "StockPulse: daily report $(date '+%Y-%m-%d')"
git push
echo "=== Published to GitHub Pages ==="
