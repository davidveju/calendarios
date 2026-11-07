#!/usr/bin/env bash
# Atajo local para el runner: scripts/actualizar.sh [--solo ID] [--timeout SEGUNDOS]
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m calendarios actualizar "$@"
