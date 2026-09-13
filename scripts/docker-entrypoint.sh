#!/usr/bin/env bash
set -euo pipefail

cd /workspace
mkdir -p data/processed data/processed/features data/processed/models

echo "=== GPU check ==="
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0))
PY

if [[ ! -f data/processed/combined_dataset.csv ]]; then
  echo "NOTE: data/processed/combined_dataset.csv not found."
  echo "      Upload your CSV to /workspace/data/processed/ before the full pipeline."
fi

exec jupyter lab \
  --ip=0.0.0.0 \
  --port="${JUPYTER_PORT:-8888}" \
  --no-browser \
  --allow-root \
  --NotebookApp.token="${JUPYTER_TOKEN:-}" \
  --notebook-dir=/workspace
