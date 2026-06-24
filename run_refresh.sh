#!/usr/bin/env bash
# Wrapper para LaunchAgent del refresh semanal de token.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
LOG="$(pwd)/token-refresh.log"
{
  echo "── $(date '+%Y-%m-%d %H:%M:%S %Z') ──"
  /usr/bin/env python3 refresh_token.py 2>&1
  echo ""
} >> "$LOG"
