#!/bin/bash
# One-command wrapper. Pure Python stdlib, no venv required.
exec python3 "$(dirname "$(readlink -f "$0")")/run.py" "$@"
