#!/usr/bin/env bash
# Paste into Vast.ai template "Onstart" (or run once over SSH).
# Image: vastai/base-image (CUDA 12.x + Jupyter), e.g. cuda-12.4 / cuda-12.8.1-auto
set -euo pipefail

export GIT_REPO="${GIT_REPO:-https://github.com/n4t5Uuu/Hybrid-AI-Text-Detector.git}"
export GIT_BRANCH="${GIT_BRANCH:-alden/data-cleaning}"
export WORKSPACE="${WORKSPACE:-/workspace}"

if [[ -f /workspace/hybrid-ai-framework/scripts/vast-bootstrap.sh ]]; then
  bash /workspace/hybrid-ai-framework/scripts/vast-bootstrap.sh
elif [[ -f /root/hybrid-ai-framework/scripts/vast-bootstrap.sh ]]; then
  bash /root/hybrid-ai-framework/scripts/vast-bootstrap.sh
else
  apt-get update -qq && apt-get install -y -qq git
  git clone --depth 1 --branch "$GIT_BRANCH" "$GIT_REPO" /workspace/hybrid-ai-framework
  bash /workspace/hybrid-ai-framework/scripts/vast-bootstrap.sh
fi
