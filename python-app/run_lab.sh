#!/usr/bin/env bash
# Usage: ./run_lab.sh 01
#        ./run_lab.sh 03_gatt_ops
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
LAB="${1:-}"
if [[ -z "$LAB" ]]; then
  echo "Usage: $0 <lab-number-or-folder>"
  echo "Example: $0 01"
  echo "         $0 03_gatt_ops"
  exit 1
fi
if [[ "$LAB" =~ ^[0-9]+$ ]]; then
  LAB=$(printf "%02d" "$LAB")
  DIR=$(find "$ROOT/labs" -maxdepth 1 -type d -name "${LAB}_*" | head -n 1)
else
  DIR="$ROOT/labs/$LAB"
fi
if [[ -z "${DIR:-}" || ! -f "$DIR/lab.py" ]]; then
  echo "Lab not found: $LAB"
  exit 1
fi
cd "$ROOT"
exec python "$DIR/lab.py" "${@:2}"
