# Docker + Vast.ai (feature extraction)

Two ways to run on a rented **4090** (or local GPU):

1. **Vast [`vastai/base-image`](https://hub.docker.com/r/vastai/base-image/)** + bootstrap script (no custom image).
2. **Your own image** from this `Dockerfile` (reproducible; push to Docker Hub).

`data/processed/combined_dataset.csv` is **never** in git — you upload or mount it.

---

## Path A — Vast official image (what you have now)

### 1. Instance settings

| Setting | Value |
|---------|--------|
| Image | `vastai/base-image` tag **CUDA 12.x** (e.g. `cuda-12.4`, `cuda-12.8.1-auto`) + Jupyter |
| Disk | **≥ 80 GB** recommended (32 GB is tight) |
| Port | **8888** open for Jupyter |

### 2. Onstart script

In the template **Onstart** field, paste the contents of [`vast/onstart.sh`](../vast/onstart.sh) from this repo  
—or after you push to GitHub, run over **SSH** once:

```bash
curl -fsSL https://raw.githubusercontent.com/n4t5Uuu/Hybrid-AI-Text-Detector/alden/data-cleaning/vast/onstart.sh | bash
```

(Change branch name if yours differs.)

That clones the repo and runs [`scripts/vast-bootstrap.sh`](../scripts/vast-bootstrap.sh) (pip, cu124 torch, CuPy, spaCy model, GPU check).

### 3. Upload the combined CSV (from your PC)

After the instance is **Running**, get **SSH host + port** from Vast, then in PowerShell from the repo root:

```powershell
.\scripts\upload-data-to-vast.ps1 -SshHost 69.x.x.x -Port 12345
```

Default local file: `data\processed\combined_dataset.csv`.

### 4. Jupyter

- Click **Open** on the instance (or use the Jupyter URL).
- Open `hybrid-ai-framework/src/notebooks/feature_extraction.ipynb`.
- Kernel: use the `venv` inside `hybrid-ai-framework` if you ran bootstrap (`.../hybrid-ai-framework/venv`).
- Set **`RUN_FULL_PIPELINE = True`**, run all cells.

---

## Path B — Custom Docker image

### Build locally

```powershell
cd hybrid-ai-framework
copy .env.docker.example .env.docker
docker compose build
docker compose up
```

Browser: http://localhost:8888 — token from `.env.docker`.

### Push for Vast

```powershell
docker login
.\scripts\publish-docker.ps1 -DockerUser YOUR_DOCKERHUB_USER
```

On Vast: set **Docker image** to `YOUR_DOCKERHUB_USER/hybrid-ai-features:cu124`, port **8888**, mount data to `/workspace/data`, upload CSV as in Path A.

---

## Checks inside the machine

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -c "import cupy, spacy; spacy.require_gpu(); print('ok')"
```

## After the run

Download `data/processed/features/` and `data/processed/models/` (scp or Jupyter), then **stop** the Vast instance.
