#!/usr/bin/env bash
# Wrapper para LaunchAgent — corre daily_engine.py con el entorno correcto.
# WHY: gh/secrets.sh viven en /usr/local/bin y /opt/homebrew/bin; launchd arranca
# con un PATH mínimo, así que lo ampliamos aquí.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
LOG="$(pwd)/daily.log"
{
  echo "── $(date '+%Y-%m-%d %H:%M:%S %Z') ──"
  /usr/bin/env python3 daily_engine.py 2>&1
  # WHY: publica captions.json para que el ERP muestre el texto de cada tarjeta futura (11-sep-2026)
  /usr/bin/env python3 export_captions.py 2>&1 || true
  echo ""
} >> "$LOG"
