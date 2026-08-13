#!/usr/bin/env bash
# Thin wrapper around scripts/bootstrap.py. Run from the repository root:
#   bash scripts/bootstrap.sh [--with-plugin]
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/bootstrap.py" "$@"
