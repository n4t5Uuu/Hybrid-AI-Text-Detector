"""
Score the hybrid detector after training.

`model_development.ipynb` uses this on the 15% validation slice (a check)
and once on the 15% test slice (the numbers that go in the write-up).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
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
    wrongly called AI. Returns accuracy, balanced accuracy, precision,
    recall, F1, ROC-AUC, FPR, and the four confusion counts.
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    human_n = fp + tn
    fpr = float(fp / human_n) if human_n else 0.0
    # Average of "AI caught" and "humans cleared", so the big AI class can't carry it alone.
    tpr = float(tp / (tp + fn)) if (tp + fn) else 0.0
    balanced_accuracy = (tpr + (1.0 - fpr)) / 2.0

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy),
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


def fpr_cluster_ci(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    groups: Sequence,
    n_boot: int = 2000,
    alpha: float = 0.05,
    random_state: int = 42,
) -> Tuple[float, float]:
    """
    FPR range from resampling whole essays instead of single passages.

    Passages cut from one essay tend to be right or wrong together, so the
    Wilson interval (which treats them as independent) comes out too narrow.
    Pass 0/1 predictions and each row's group_id. Returns (low, high).
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    human = y_true == 0
    if not human.any():
        return (0.0, 0.0)

    # False positives and passage counts per human essay.
    per_essay = (
        pd.DataFrame({"group": np.asarray(groups)[human], "fp": y_pred[human]})
        .groupby("group")["fp"]
        .agg(["sum", "count"])
    )
    fp_per_essay = per_essay["sum"].to_numpy(dtype=float)
    n_per_essay = per_essay["count"].to_numpy(dtype=float)

    # Redraw the essays with replacement many times and recompute FPR each time.
    rng = np.random.default_rng(random_state)
    picks = rng.integers(0, len(per_essay), size=(n_boot, len(per_essay)))
    rates = fp_per_essay[picks].sum(axis=1) / n_per_essay[picks].sum(axis=1)
    low, high = np.quantile(rates, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(low), float(high)


def length_baseline_report(
    train_words: Sequence[float],
    y_train: Sequence[int],
    test_words: Sequence[float],
    y_test: Sequence[int],
    test_sources: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """
    How far word count alone gets. The hybrid has to clearly beat this.

    On train we learn which way to read length (shorter = AI or longer = AI)
    and the one cut-off with the best balanced accuracy. Then we score test:
    all rows, and each AI source against all human test rows.
    """
    train_words = np.asarray(train_words, dtype=float)
    test_words = np.asarray(test_words, dtype=float)
    y_train = np.asarray(y_train).astype(int)
    y_test = np.asarray(y_test).astype(int)

    # Pick the direction on train: a higher score always means "more AI".
    sign = -1.0 if roc_auc_score(y_train, -train_words) >= 0.5 else 1.0
    train_score = sign * train_words
    test_score = sign * test_words

    # Try cut-offs at train percentiles and keep the best balanced accuracy.
    best_cut, best_bal = 0.0, -1.0
    for cut in np.unique(np.quantile(train_score, np.linspace(0.0, 1.0, 201))):
        called_ai = train_score >= cut
        bal = (called_ai[y_train == 1].mean() + 1.0 - called_ai[y_train == 0].mean()) / 2.0
        if bal > best_bal:
            best_cut, best_bal = float(cut), float(bal)
    rule = (
        f"AI if words <= {-best_cut:.0f}" if sign < 0 else f"AI if words >= {best_cut:.0f}"
    )

    scopes = [("all AI sources", np.ones(len(y_test), dtype=bool))]
    if test_sources is not None:
        sources = np.asarray(test_sources).astype(str)
        for source in sorted(np.unique(sources[y_test == 1])):
            scopes.append((source, (y_test == 0) | (sources == source)))

    rows = []
    for scope, mask in scopes:
        y, score = y_test[mask], test_score[mask]
        called_ai = score >= best_cut
        fpr = float(called_ai[y == 0].mean())
        recall = float(called_ai[y == 1].mean())
        rows.append(
            {
                "scope": scope,
                "rule": rule,
                "roc_auc": float(roc_auc_score(y, score)),
                "balanced_accuracy": (recall + 1.0 - fpr) / 2.0,
                "fpr": fpr,
                "recall": recall,
                "n_human": int((y == 0).sum()),
                "n_ai": int((y == 1).sum()),
            }
        )
    return pd.DataFrame(rows)


def per_source_report(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    sources: Sequence[str],
    threshold: float = 0.5,
) -> pd.DataFrame:
    """
    Break results down by where each text came from.

    Human rows get their FPR. Each AI source gets its recall (share caught)
    and its ROC-AUC against all human rows, so a weak result on Claude or
    Gemini can't hide behind MGTBench, which is ~93% of the AI rows.
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    sources = np.asarray(sources).astype(str)
    called_ai = y_prob >= threshold
    human = y_true == 0

    rows = []
    for source in sorted(np.unique(sources)):
        mask = sources == source
        if not y_true[mask].any():
            rows.append(
                {
                    "source": source,
                    "class": "human",
                    "n": int(mask.sum()),
                    "fpr": float(called_ai[mask].mean()),
                    "recall": np.nan,
                    "roc_auc": np.nan,
                }
            )
            continue
        ai = mask & (y_true == 1)
        both = human | ai
        rows.append(
            {
                "source": source,
                "class": "AI",
                "n": int(ai.sum()),
                "fpr": np.nan,
                "recall": float(called_ai[ai].mean()),
                "roc_auc": float(roc_auc_score(y_true[both], y_prob[both])) if human.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


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
