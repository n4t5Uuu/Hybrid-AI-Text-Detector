"""
Paste **S** and **E** side by side into **H** (one wide row per essay).

The hybrid XGBoost model trains on **H**.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

import numpy as np


def fuse_spacy_electra(
    spacy_matrix: np.ndarray,
    electra_matrix: np.ndarray,
    spacy_feature_names: Sequence[str],
) -> tuple[np.ndarray, List[str]]:
    """
    One row per essay: spaCy columns, then ELECTRA columns.

    spaCy and ELECTRA need the same essay order and the same number of rows.
    """
    if spacy_matrix.shape[0] != electra_matrix.shape[0]:
        raise ValueError(
            f"Row mismatch: S has {spacy_matrix.shape[0]} rows, E has {electra_matrix.shape[0]}"
        )
    # One wide row per essay: spaCy stats, then ELECTRA numbers.
    hybrid = np.hstack([spacy_matrix, electra_matrix]).astype(np.float32, copy=False)
    electra_names = [f"electra_{i}" for i in range(electra_matrix.shape[1])]
    hybrid_names = list(spacy_feature_names) + electra_names
    return hybrid, hybrid_names


def save_hybrid_features(
    hybrid: np.ndarray,
    hybrid_names: Sequence[str],
    output_dir: Path,
) -> Path:
    """Save **H** and the column names for training or a later reload."""
    output_dir.mkdir(parents=True, exist_ok=True)
    npy_path = output_dir / "hybrid_features.npy"
    np.save(npy_path, hybrid)
    names_path = output_dir / "hybrid_feature_names.json"
    names_path.write_text(json.dumps(list(hybrid_names), indent=2), encoding="utf-8")
    return npy_path
