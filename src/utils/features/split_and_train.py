"""
Split 70/15/15, build TF-IDF **R**, train four XGBoost models.

Word weights for **R** come from train essays only. The same train/val/test rows
cut **H**, **S**, **E**, and **R**. Test rows are saved for later — not tuned here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from xgboost import XGBClassifier


def _stratify_labels(labels: Sequence, subjects: Optional[Sequence] = None) -> np.ndarray:
    labels_s = pd.Series(labels).astype(str)
    if subjects is None:
        return labels_s.to_numpy()
    # Human/AI plus subject so each split keeps a similar mix.
    subj = pd.Series(subjects).fillna("").astype(str)
    return (labels_s + "__" + subj).to_numpy()


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
    Which row numbers are train, val, or test — keeps labels and subjects balanced.

    Use the same three index lists on **H**, **S**, **E**, and **R** in the notebook.
    """
    if abs(train_size + val_size + test_size - 1.0) > 1e-6:
        raise ValueError("train_size + val_size + test_size must equal 1.0")
    indices = np.arange(n_rows)
    strat = _stratify_labels(labels, subjects)
    test_ratio = test_size
    train_val_ratio = train_size + val_size
    # Peel off 15% test, then split the remaining 85% into train and val.
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


def fit_tfidf_on_train(
    train_texts: Sequence[str],
    max_features: int = 10_000,
    ngram_range: Tuple[int, int] = (1, 2),
) -> TfidfVectorizer:
    """Learn TF-IDF word weights from train essays only (the text-only baseline)."""
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=2,
        sublinear_tf=True,
    )
    vectorizer.fit(train_texts)
    return vectorizer


def transform_tfidf(vectorizer: TfidfVectorizer, texts: Sequence[str]) -> np.ndarray:
    return vectorizer.transform(texts).toarray().astype(np.float32)


def default_xgb_param_grid() -> Dict[str, Any]:
    return {
        "max_depth": [3, 5, 7],
        "learning_rate": [0.05, 0.1],
        "n_estimators": [100, 200],
        "subsample": [0.8, 1.0],
    }


def train_xgboost_gpu(
    x_train: np.ndarray,
    y_train: np.ndarray,
    param_grid: Optional[Dict[str, Any]] = None,
    cv_folds: int = 5,
    random_state: int = 42,
    use_cuda: bool = True,
) -> Tuple[XGBClassifier, GridSearchCV]:
    """Try a few hyperparameter combos on train data; keep the one that scores best."""
    if param_grid is None:
        param_grid = default_xgb_param_grid()
    device = "cuda" if use_cuda else "cpu"
    tree_method = "hist"
    # Same classifier setup for hybrid, spaCy-only, ELECTRA-only, and TF-IDF runs.
    base = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        device=device,
        tree_method=tree_method,
        n_jobs=1,
        random_state=random_state,
    )
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    search = GridSearchCV(
        base,
        param_grid,
        cv=cv,
        scoring="roc_auc",
        n_jobs=1,
        verbose=1,
    )
    search.fit(x_train, y_train)
    return search.best_estimator_, search


def save_split_and_models(
    output_dir: Path,
    idx_train: np.ndarray,
    idx_val: np.ndarray,
    idx_test: np.ndarray,
    models: Dict[str, XGBClassifier],
    vectorizer: Optional[TfidfVectorizer] = None,
    cv_results: Optional[Dict[str, Any]] = None,
) -> None:
    """Save the splits, all four models, the TF-IDF object, and how tuning went."""
    output_dir.mkdir(parents=True, exist_ok=True)
    # Row picks so evaluation later uses the same held-out essays.
    np.save(output_dir / "idx_train.npy", idx_train)
    np.save(output_dir / "idx_val.npy", idx_val)
    np.save(output_dir / "idx_test.npy", idx_test)
    for name, model in models.items():
        model.save_model(str(output_dir / f"xgb_{name}.json"))
    if vectorizer is not None:
        joblib.dump(vectorizer, output_dir / "tfidf_vectorizer.joblib")
    if cv_results is not None:
        (output_dir / "cv_results.json").write_text(
            json.dumps(cv_results, indent=2, default=str),
            encoding="utf-8",
        )
