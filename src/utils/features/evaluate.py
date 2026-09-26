"""
Score the hybrid detector after training.

`model_development.ipynb` uses this on the 15% validation slice (a check)
and once on the 15% test slice (the numbers that go in the write-up).
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_report_row(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Turn predicted AI probabilities into one row of thesis metrics.

    Label 1 is AI. FPR is the share of human essays (label 0) that we
    wrongly called AI. Returns accuracy, precision, recall, F1, ROC-AUC,
    FPR, and the four confusion counts.
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    human_n = fp + tn
    fpr = float(fp / human_n) if human_n else 0.0

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0,
        "fpr": fpr,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def hybrid_cv_score(y_true, y_score) -> float:
    """
    Rank a hyperparameter combo for this thesis: ROC-AUC minus FPR.

    ROC-AUC is already near 1.0 on this corpus (almost all essays are AI),
    so subtracting FPR is what actually prefers fewer false AI calls on
    human writing. Grid search maximises this number.
    """
    y_score = np.asarray(y_score)
    if y_score.ndim == 2:
        y_score = y_score[:, 1]
    row = classification_report_row(y_true, y_score)
    return float(row["roc_auc"] - row["fpr"])


def describe_fit(train: Dict[str, Any], val: Dict[str, Any], test: Dict[str, Any]) -> str:
    """
    One-line read of train vs val vs test: overfit, underfit, or close enough.

    FPR is the main tell. A big jump from train to val means the model
    memorised train humans. Low scores on every split means it never learned.
    """
    train_fpr, val_fpr, test_fpr = train["fpr"], val["fpr"], test["fpr"]
    train_auc, val_auc = train["roc_auc"], val["roc_auc"]

    if train_auc < 0.90 and val_auc < 0.90:
        return (
            "Underfit: train and validation ROC-AUC are both low. "
            "The model is not separating human vs AI well yet."
        )
    if val_fpr - train_fpr >= 0.03 or train_auc - val_auc >= 0.02:
        return (
            f"Overfit on human essays: train FPR={train_fpr:.1%} but "
            f"validation FPR={val_fpr:.1%} (test {test_fpr:.1%}). "
            "It looks perfect on rows it trained on, then slips on new humans."
        )
    if abs(test_fpr - val_fpr) >= 0.03:
        return (
            f"Close on ranking, noisy FPR: validation FPR={val_fpr:.1%}, "
            f"test FPR={test_fpr:.1%}. Human counts per fold are small, so "
            "treat the FPR gap with caution."
        )
    return (
        f"Just right: train/val/test FPR are {train_fpr:.1%} / {val_fpr:.1%} / "
        f"{test_fpr:.1%}, and ROC-AUC stays high on held-out rows."
    )


def fpr_wilson_interval(fp: int, human_n: int, z: float = 1.96) -> Tuple[float, float]:
    """
    Wilson score interval for the human false-positive rate (fp / human_n).

    Use on the test slice only; ~302 humans means a few mistakes move the rate a lot.
    """
    if human_n <= 0:
        return (0.0, 0.0)
    p = fp / human_n
    z2 = z * z
    denom = 1.0 + z2 / human_n
    center = (p + z2 / (2.0 * human_n)) / denom
    margin = (z / denom) * np.sqrt(p * (1.0 - p) / human_n + z2 / (4.0 * human_n * human_n))
    low = float(max(0.0, center - margin))
    high = float(min(1.0, center + margin))
    return low, high


def feature_group_importance(
    importances: Sequence[float],
    feature_names: Sequence[str],
    n_spacy: int,
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    Split XGBoost gain importances between spaCy (first n_spacy columns) and ELECTRA.
    """
    imp = np.asarray(importances, dtype=np.float64)
    names = list(feature_names)
    if imp.shape[0] != len(names):
        raise ValueError(f"importances length {imp.shape[0]} != names length {len(names)}")
    n_spacy = int(n_spacy)
    spacy_gain = float(imp[:n_spacy].sum())
    electra_gain = float(imp[n_spacy:].sum())
    total = spacy_gain + electra_gain
    if total <= 0:
        spacy_share = electra_share = 0.0
    else:
        spacy_share = spacy_gain / total
        electra_share = electra_gain / total
    order = np.argsort(-imp)
    top: List[Dict[str, Any]] = [
        {"feature": names[i], "gain": float(imp[i])} for i in order[:top_k]
    ]
    return {
        "spacy_gain": spacy_gain,
        "electra_gain": electra_gain,
        "spacy_share": spacy_share,
        "electra_share": electra_share,
        "top_features": top,
    }
