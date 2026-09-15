"""
70 / 15 / 15 train–val–test split for the combined essay table.

Keeps human vs AI balance and subject (discipline) mix similar in each fold.
`data_splitting.ipynb` writes indices under data/processed/splits/; training
and feature notebooks reuse those row picks on **H**, **S**, **E**, and **R**.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def _stratify_labels(labels: Sequence, subjects: Optional[Sequence] = None) -> np.ndarray:
    labels_s = pd.Series(labels).astype(str)
    if subjects is None:
        return labels_s.to_numpy()
    subj = pd.Series(subjects).fillna("").astype(str).copy()
    frame = pd.DataFrame({"label": labels_s, "subject": subj})

    # sklearn needs at least two rows per stratification bucket.
    key = frame["label"] + "__" + frame["subject"]
    counts = key.value_counts()
    singleton_mask = counts == 1
    if singleton_mask.any():
        # One-off disciplines still need a bucket mate for sklearn — donor is stratify-only.
        for strat_key in counts[singleton_mask].index:
            lab, subject = strat_key.split("__", 1)
            same_label = frame["label"] == lab
            pool = frame.loc[same_label, "subject"]
            pool_counts = pool.value_counts()
            # Borrow the smallest discipline that already has 2+ essays in this class.
            candidates = pool_counts[pool_counts >= 2]
            if candidates.empty:
                continue
            donor = candidates.idxmin()
            frame.loc[same_label & (frame["subject"] == subject), "subject"] = donor

    return (frame["label"] + "__" + frame["subject"]).to_numpy()


def stratified_train_val_test_split(
    n_rows: int,
    labels: Sequence,
    subjects: Optional[Sequence] = None,
    train_size: float = 0.7,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return row indices for train, validation, and test (70% / 15% / 15%).

    Stratifies on class label and subject (discipline). Use the same three
    index arrays to slice every feature matrix built from the combined table.
    """
    if abs(train_size + val_size + test_size - 1.0) > 1e-6:
        raise ValueError("train_size + val_size + test_size must equal 1.0")
    if len(labels) != n_rows:
        raise ValueError(f"labels length {len(labels)} != n_rows {n_rows}")
    if subjects is not None and len(subjects) != n_rows:
        raise ValueError(f"subjects length {len(subjects)} != n_rows {n_rows}")

    indices = np.arange(n_rows)
    strat = _stratify_labels(labels, subjects)
    test_ratio = test_size
    train_val_ratio = train_size + val_size

    # Hold out 15% test first, then split the remaining 85% into 70% train and 15% val.
    idx_train_val, idx_test = train_test_split(
        indices,
        test_size=test_ratio,
        random_state=random_state,
        stratify=strat,
    )
    strat_tv = strat[idx_train_val]
    val_ratio_of_tv = val_size / train_val_ratio
    idx_train, idx_val = train_test_split(
        idx_train_val,
        test_size=val_ratio_of_tv,
        random_state=random_state,
        stratify=strat_tv,
    )
    return idx_train, idx_val, idx_test


def split_sizes(n_rows: int, train_size: float = 0.7, val_size: float = 0.15) -> Dict[str, int]:
    """Rough counts for reporting — actual sizes come from the stratified split."""
    test_size = 1.0 - train_size - val_size
    return {
        "train": int(round(n_rows * train_size)),
        "val": int(round(n_rows * val_size)),
        "test": int(round(n_rows * test_size)),
    }


def split_balance_table(
    df: pd.DataFrame,
    idx_train: np.ndarray,
    idx_val: np.ndarray,
    idx_test: np.ndarray,
    label_col: str = "label",
    subject_col: str = "subject",
) -> pd.DataFrame:
    """
    Count labels and subjects per split so we can check the stratification worked.

    Returns a long table: split, label, subject, count.
    """
    parts = []
    for name, idx in ("train", idx_train), ("val", idx_val), ("test", idx_test):
        chunk = df.iloc[idx][[label_col, subject_col]].copy()
        chunk["split"] = name
        parts.append(chunk)
    stacked = pd.concat(parts, ignore_index=True)
    return (
        stacked.groupby(["split", label_col, subject_col], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["split", label_col, subject_col])
    )


def label_proportions_by_split(
    df: pd.DataFrame,
    idx_train: np.ndarray,
    idx_val: np.ndarray,
    idx_test: np.ndarray,
    label_col: str = "label",
) -> pd.DataFrame:
    """Human vs AI share in each split — should stay close to the full table."""
    rows = []
    for name, idx in ("train", idx_train), ("val", idx_val), ("test", idx_test):
        labels = df.iloc[idx][label_col]
        n = len(labels)
        for label_val, cnt in labels.value_counts().items():
            rows.append(
                {
                    "split": name,
                    "label": label_val,
                    "count": int(cnt),
                    "proportion": cnt / n if n else 0.0,
                }
            )
    return pd.DataFrame(rows).sort_values(["split", "label"])


def save_split_artifacts(
    output_dir: Path,
    idx_train: np.ndarray,
    idx_val: np.ndarray,
    idx_test: np.ndarray,
    df: Optional[pd.DataFrame] = None,
    random_state: int = 42,
    train_size: float = 0.7,
    val_size: float = 0.15,
    test_size: float = 0.15,
) -> Path:
    """
    Write idx_*.npy, an optional row-level assignment CSV, and a small JSON summary.

    Returns the output directory path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "idx_train.npy", idx_train)
    np.save(output_dir / "idx_val.npy", idx_val)
    np.save(output_dir / "idx_test.npy", idx_test)

    if df is not None:
        assignment = pd.DataFrame({"row_id": np.arange(len(df))})
        assignment["split"] = "train"
        assignment.loc[idx_val, "split"] = "val"
        assignment.loc[idx_test, "split"] = "test"
        for col in ("label", "source", "subject"):
            if col in df.columns:
                assignment[col] = df[col].values
        assignment.to_csv(output_dir / "split_assignments.csv", index=False)

    summary = {
        "random_state": random_state,
        "train_size": train_size,
        "val_size": val_size,
        "test_size": test_size,
        "n_rows": int(len(idx_train) + len(idx_val) + len(idx_test)),
        "n_train": int(len(idx_train)),
        "n_val": int(len(idx_val)),
        "n_test": int(len(idx_test)),
    }
    if df is not None and "label" in df.columns:
        overall = df["label"].value_counts(normalize=True).to_dict()
        summary["overall_label_proportion"] = {str(k): float(v) for k, v in overall.items()}
        by_split = label_proportions_by_split(df, idx_train, idx_val, idx_test)
        prop_by_split: Dict[str, Dict[str, float]] = {}
        for split_name, group in by_split.groupby("split"):
            prop_by_split[str(split_name)] = {
                str(row.label): float(row.proportion) for row in group.itertuples()
            }
        summary["label_proportion_by_split"] = prop_by_split
    (output_dir / "split_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return output_dir


def load_split_indices(splits_dir: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load train / val / test row indices written by save_split_artifacts."""
    splits_dir = Path(splits_dir)
    for name in ("train", "val", "test"):
        path = splits_dir / f"idx_{name}.npy"
        if not path.exists():
            raise FileNotFoundError(f"Missing split file: {path} (run data_splitting.ipynb first)")
    return (
        np.load(splits_dir / "idx_train.npy"),
        np.load(splits_dir / "idx_val.npy"),
        np.load(splits_dir / "idx_test.npy"),
    )
