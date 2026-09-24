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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import make_scorer
from sklearn.model_selection import GridSearchCV, ParameterGrid, StratifiedKFold
from xgboost import XGBClassifier

from .evaluate import classification_report_row, hybrid_cv_score


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
    """
    Stricter grid after the run that scored every training human correctly.

    Leaves must cover more essays (min_child_weight), extra splits are
    penalized (reg_lambda, gamma), and depth 1 is allowed to win.
    n_estimators is only a cap; early stopping cuts it on validation.
    scale_pos_weight stays at 1 so the loss does not chase the rare human class.
    """
    return {
        "max_depth": [1, 2],
        "learning_rate": [0.05, 0.1],
        "n_estimators": [400],
        "min_child_weight": [10, 50],
        "subsample": [0.8],
        "reg_lambda": [1.0, 10.0],
        "gamma": [0.0, 1.0],
    }


def require_cuda_for_training() -> None:
    """Stop if the GPU is missing so grid search never silently uses CPU."""
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is required to check CUDA before XGBoost GPU training.") from exc
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available. Run model_development.ipynb on a GPU machine."
        )


def features_on_gpu(x: np.ndarray):
    """Copy a feature matrix onto the GPU so XGBoost does not fall back to CPU data."""
    import cupy as cp

    return cp.asarray(np.ascontiguousarray(x, dtype=np.float32))


def smoke_test_xgboost_cuda(random_state: int = 42) -> None:
    """Tiny GPU fit so we know XGBoost can use CUDA before the full grid search."""
    require_cuda_for_training()
    x = features_on_gpu(np.random.randn(64, 4).astype(np.float32))
    y = np.array([0, 1] * 32)
    clf = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        device="cuda",
        tree_method="hist",
        n_estimators=2,
        max_depth=2,
        n_jobs=1,
        random_state=random_state,
    )
    clf.fit(x, y)
    clf.predict_proba(x)


class ValidationSearchResult:
    """Fields the notebook already reads off GridSearchCV, filled from the validation slice."""

    def __init__(
        self,
        best_estimator: XGBClassifier,
        best_params: Dict[str, Any],
        best_score: float,
        cv_results: Dict[str, list],
        best_iteration: int,
        selection_note: str,
    ) -> None:
        self.best_estimator_ = best_estimator
        self.best_params_ = best_params
        self.best_score_ = best_score
        self.cv_results_ = cv_results
        self.best_iteration_ = best_iteration
        self.selection_note_ = selection_note


def _stopped_at(model: XGBClassifier, cap: int) -> int:
    iteration = getattr(model, "best_iteration", None)
    if iteration is None:
        return int(cap)
    return int(iteration) + 1


def train_xgboost_gpu(
    x_train: np.ndarray,
    y_train: np.ndarray,
    param_grid: Optional[Dict[str, Any]] = None,
    cv_folds: int = 5,
    random_state: int = 42,
    use_cuda: bool = True,
    x_val: Optional[np.ndarray] = None,
    y_val: Optional[np.ndarray] = None,
    early_stopping_rounds: int = 30,
) -> Tuple[XGBClassifier, Any]:
    """
    Pick hyperparameters on the validation slice, not on a refit of every train row.

    Each combo may grow up to n_estimators trees and stops when validation
    logloss has not improved for early_stopping_rounds rounds. The winner is
    the combo with the highest validation ROC-AUC minus FPR. A depth-1 model
    replaces it when its validation FPR is within half a point, so extra trees
    are not kept just to memorize training humans. The test slice is not used.
    """
    if param_grid is None:
        param_grid = default_xgb_param_grid()
    if (x_val is None) ^ (y_val is None):
        raise ValueError("Pass both x_val and y_val, or neither.")
    if use_cuda:
        require_cuda_for_training()
    device = "cuda" if use_cuda else "cpu"
    if x_val is None:
        return _train_with_train_cv(
            x_train, y_train, param_grid, cv_folds, random_state, device, use_cuda
        )
    return _train_with_validation(
        x_train,
        y_train,
        x_val,
        y_val,
        param_grid,
        random_state,
        device,
        use_cuda,
        early_stopping_rounds,
    )


def _train_with_train_cv(
    x_train: np.ndarray,
    y_train: np.ndarray,
    param_grid: Dict[str, Any],
    cv_folds: int,
    random_state: int,
    device: str,
    use_cuda: bool,
) -> Tuple[XGBClassifier, GridSearchCV]:
    """Fallback when no validation matrix is passed (older notebooks)."""
    x_fit = features_on_gpu(x_train) if use_cuda else x_train
    base = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        device=device,
        tree_method="hist",
        n_jobs=1,
        random_state=random_state,
    )
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    search = GridSearchCV(
        base,
        param_grid,
        cv=cv,
        scoring=make_scorer(hybrid_cv_score, response_method="predict_proba"),
        n_jobs=1,
        verbose=1,
    )
    search.fit(x_fit, y_train)
    return search.best_estimator_, search


def _train_with_validation(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    param_grid: Dict[str, Any],
    random_state: int,
    device: str,
    use_cuda: bool,
    early_stopping_rounds: int,
) -> Tuple[XGBClassifier, ValidationSearchResult]:
    x_fit = features_on_gpu(x_train) if use_cuda else x_train
    x_eval = features_on_gpu(x_val) if use_cuda else x_val
    y_eval = np.asarray(y_val)
    candidates = list(ParameterGrid(param_grid))
    rows: Dict[str, list] = {
        "mean_test_score": [],
        "std_test_score": [],
        "val_fpr": [],
        "best_iteration": [],
    }
    best_model: Optional[XGBClassifier] = None
    best_score = -np.inf
    best_fpr = np.inf
    best_params: Dict[str, Any] = {}
    stump_model: Optional[XGBClassifier] = None
    stump_score = -np.inf
    stump_fpr = np.inf
    stump_params: Dict[str, Any] = {}

    for i, params in enumerate(candidates, start=1):
        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            device=device,
            tree_method="hist",
            n_jobs=1,
            random_state=random_state,
            early_stopping_rounds=early_stopping_rounds,
            **params,
        )
        model.fit(
            x_fit,
            y_train,
            eval_set=[(x_eval, y_eval)],
            verbose=False,
        )
        proba = model.predict_proba(x_eval)[:, 1]
        score = hybrid_cv_score(y_eval, proba)
        fpr = classification_report_row(y_eval, proba)["fpr"]
        trees = _stopped_at(model, int(params["n_estimators"]))
        summary = " ".join(f"{key}={value}" for key, value in params.items())
        print(
            f"[{i}/{len(candidates)}] {summary} "
            f"trees={trees} val_score={score:.4f} val_fpr={fpr:.3%}"
        )
        for key, value in params.items():
            rows.setdefault(f"param_{key}", []).append(value)
        rows["mean_test_score"].append(score)
        rows["std_test_score"].append(0.0)
        rows["val_fpr"].append(fpr)
        rows["best_iteration"].append(trees)
        if score > best_score:
            best_model, best_score, best_fpr, best_params = model, score, fpr, dict(params)
        if int(params["max_depth"]) == 1 and score > stump_score:
            stump_model, stump_score, stump_fpr, stump_params = model, score, fpr, dict(params)

    if best_model is None:
        raise RuntimeError("Parameter grid was empty.")

    chosen, chosen_params, chosen_score, note = best_model, best_params, best_score, (
        "Kept the validation winner."
    )
    if (
        stump_model is not None
        and stump_params != best_params
        and stump_fpr <= best_fpr + 0.005
    ):
        chosen, chosen_params, chosen_score = stump_model, stump_params, stump_score
        note = (
            f"Shipped the depth-1 model: validation FPR {stump_fpr:.1%} is within "
            f"0.5 points of the best FPR {best_fpr:.1%}."
        )
    elif int(chosen_params.get("max_depth", 0)) == 1:
        note = "The depth-1 model won validation outright."

    trees = _stopped_at(chosen, int(chosen_params["n_estimators"]))
    print(note, f"Trees kept: {trees}.")
    return chosen, ValidationSearchResult(
        chosen, chosen_params, float(chosen_score), rows, trees, note
    )


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


def save_hybrid_model(
    output_dir: Path,
    model: XGBClassifier,
    cv_results: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Write the hybrid XGBoost file and how the grid search went.

    Does not touch idx_*.npy — those stay in data/processed/splits/.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(str(output_dir / "xgb_hybrid.json"))
    if cv_results is not None:
        (output_dir / "cv_results.json").write_text(
            json.dumps(cv_results, indent=2, default=str),
            encoding="utf-8",
        )
    return output_dir
