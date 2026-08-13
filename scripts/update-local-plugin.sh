#!/usr/bin/env bash
# Thin wrapper around the cross-platform update_local_plugin.py.
# Run from the repository root:
#   bash scripts/update-local-plugin.sh
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/update_local_plugin.py" "$@"
