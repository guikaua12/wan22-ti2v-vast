#!/usr/bin/env bash
set -euo pipefail

EXECUTOR_DIR="${EXECUTOR_DIR:-/workspace/flourn-gpu-executor}"

python3 -m pip install --no-cache-dir psycopg[binary] boto3 requests 2>/dev/null || true

cd /workspace/ComfyUI
python3 main.py --listen 0.0.0.0 --port 18188 &

cd "$EXECUTOR_DIR"
python3 executor/executor.py
