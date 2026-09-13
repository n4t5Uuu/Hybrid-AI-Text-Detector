# Feature extraction on NVIDIA GPU (Vast.ai custom image or local docker compose)
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt \
    && python -m spacy download en_core_web_sm

COPY src ./src
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY scripts/vast-bootstrap.sh ./scripts/vast-bootstrap.sh
COPY vast ./vast
COPY README.md AGENTS.md docs/DOCKER.md ./

RUN chmod +x /usr/local/bin/docker-entrypoint.sh ./scripts/vast-bootstrap.sh ./vast/onstart.sh

ENV PYTHONPATH=/workspace/src
ENV JUPYTER_PORT=8888

EXPOSE 8888

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
