#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --no-cache-dir psycopg[binary] boto3 requests

if [[ -x /start.sh ]]; then
  /start.sh &
else
  cd /workspace/ComfyUI
  python3 main.py --listen 0.0.0.0 --port 18188 &
fi

cd /workspace/flourn-gpu-executor
python3 executor/executor.py
