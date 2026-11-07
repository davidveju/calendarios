#!/usr/bin/env bash
# Ejecuta todos los tests del monorepo (paquete común + cada calendario).
set -euo pipefail
cd "$(dirname "$0")/.."

# En tests los avisos son parte del caso de prueba, no anotaciones del workflow.
export CALENDARIOS_TEST=1

encontrados=0
while IFS= read -r directorio; do
  if compgen -G "$directorio/test_*.py" >/dev/null; then
    encontrados=1
    echo
    echo "==> Tests de $directorio"
    python3 -m unittest discover -s "$directorio" -t . "$@"
  fi
done < <(find . -type d -name tests -not -path './.git/*' -not -path '*/__pycache__/*' | sort)

if [ "$encontrados" -eq 0 ]; then
  echo "No se encontraron tests." >&2
  exit 1
fi
