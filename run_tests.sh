#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if ! command -v uv &>/dev/null; then
    echo "uv not found. Install it: https://docs.astral.sh/uv/#installation"
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    uv venv "$VENV_DIR"
fi

echo "Installing dependencies..."
uv sync --project "$SCRIPT_DIR" --group test --no-install-project

echo ""
echo "Running tests..."
uv run --project "$SCRIPT_DIR" pytest "$SCRIPT_DIR/tests/" -v "$@"
