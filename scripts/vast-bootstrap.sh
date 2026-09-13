#!/usr/bin/env bash
# Run on Vast.ai (vastai/base-image or SSH) after the instance is up.
set -euo pipefail

REPO_URL="${GIT_REPO:-https://github.com/n4t5Uuu/Hybrid-AI-Text-Detector.git}"
REPO_BRANCH="${GIT_BRANCH:-alden/data-cleaning}"
WORKDIR="${WORKSPACE:-/workspace}"
PROJECT_DIR="$WORKDIR/hybrid-ai-framework"

mkdir -p "$WORKDIR/data/processed"

if [[ ! -d "$PROJECT_DIR/.git" ]]; then
  echo "Cloning $REPO_URL ($REPO_BRANCH) ..."
  git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$PROJECT_DIR"
else
  echo "Repo exists; pulling ..."
  cd "$PROJECT_DIR" && git pull --ff-only || true
fi

cd "$PROJECT_DIR"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
# shellcheck source=/dev/null
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install "cupy-cuda12x[ctk]"
python -m spacy download en_core_web_sm

export PYTHONPATH="$PROJECT_DIR/src"

echo "=== GPU check ==="
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0))
import spacy
spacy.require_gpu()
print("spaCy GPU OK")
PY

if [[ -f data/processed/combined_dataset.csv ]]; then
  echo "Found data/processed/combined_dataset.csv"
else
  echo "MISSING: $PROJECT_DIR/data/processed/combined_dataset.csv"
  echo "Upload from your PC (see scripts/upload-data-to-vast.ps1)"
fi

echo "Done. Open notebook: src/notebooks/feature_extraction.ipynb"
echo "Set RUN_FULL_PIPELINE = True for full ~157k run."
