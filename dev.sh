#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "Error: .env not found in ${ROOT_DIR}." >&2
  exit 1
fi

echo "Loading environment from .env..."
set -a
source .env
set +a

if [[ "${SKIP_PIP_INSTALL:-0}" != "1" ]]; then
  echo "Installing packages..."
  pip install -e .
else
  echo "Skipping package installation (SKIP_PIP_INSTALL=1)."
fi

echo "Starting API..."
cd apps/api
uvicorn src.main:app --reload --port "${PORT:-8000}"
