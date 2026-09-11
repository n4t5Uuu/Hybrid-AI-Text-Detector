"""
ELECTRA meaning vector per essay — that's **E**.

Run after spaCy in the notebook so you're not holding two big models on the GPU.
Keep essays in the same order as **S** before you fuse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import torch
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer


def resolve_torch_device(prefer_cuda: bool = True) -> torch.device:
    """Use the GPU for the full run; CPU only when prefer_cuda=False (quick tests)."""
    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")
    if prefer_cuda:
        raise RuntimeError(
            "CUDA is not available. Install cu121 PyTorch and run on a GPU machine "
            "before the full ~157k extraction."
        )
    return torch.device("cpu")


def load_electra(model_name: str = "google/electra-base-discriminator", prefer_cuda: bool = True):
    """Load ELECTRA ready to read essays (we don't train it here)."""
    device = resolve_torch_device(prefer_cuda=prefer_cuda)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    model.to(device)
    # Frozen — we're only reading essays, not updating weights.
    for p in model.parameters():
        p.requires_grad = False
    return tokenizer, model, device


def _normalize_text(text) -> str:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""

    s = str(text).strip()
    return s if s else ""


def extract_electra_embeddings(
    texts: Sequence,
    tokenizer,
    model,
    device: torch.device,
    max_length: int = 512,
    batch_size: int = 16,
    checkpoint_path: Optional[Path] = None,
    checkpoint_every: int = 500,
    show_progress: bool = True,
) -> np.ndarray:
    """
    Embed each essay with ELECTRA (768 numbers per row).

    Pass checkpoint_path to save progress during a long run. Empty essays are
    cleared to zero so they match spaCy.
    """
    n = len(texts)
    hidden = model.config.hidden_size
    normalized = [_normalize_text(t) for t in texts]

    # Long run: write rows to disk as we go; short run: keep everything in RAM.
    if checkpoint_path is not None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            checkpoint_path,
            mode="w+",
            dtype=np.float32,
            shape=(n, hidden),
        )
    else:
        out = np.zeros((n, hidden), dtype=np.float32)

    batches = range(0, n, batch_size)
    if show_progress:
        batches = tqdm(batches, total=(n + batch_size - 1) // batch_size, desc="ELECTRA CLS E")

    with torch.no_grad():
        for start in batches:
            end = min(start + batch_size, n)
            batch_texts = normalized[start:end]
            encoded = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            outputs = model(**encoded)
            # First token position is the sentence-level vector we use for **E**.
            cls = outputs.last_hidden_state[:, 0, :].detach().cpu().numpy().astype(np.float32)
            out[start:end] = cls
            if checkpoint_path is not None and (end % checkpoint_every == 0 or end == n):
                out.flush()

    # Same rule as spaCy: empty essay → all zeros.
    for i, text in enumerate(normalized):
        if not text:
            out[i] = 0.0

    if checkpoint_path is not None:
        del out
        return np.load(checkpoint_path, mmap_mode="r")
    return out
