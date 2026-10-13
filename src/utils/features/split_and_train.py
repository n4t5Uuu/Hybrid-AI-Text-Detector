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
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import make_scorer
from sklearn.model_selection import GridSearchCV, ParameterGrid, StratifiedGroupKFold
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


def downsample_ai_train(
    x: np.ndarray,
    y: np.ndarray,
    ai_per_human: int = 10,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Keep every human row; sample AI rows so train is not 98% AI by count.

    Val and test must use the full slices — only call this on train matrices.
    """
    y_arr = np.asarray(y).astype(int)
    human_idx = np.flatnonzero(y_arr == 0)
    ai_idx = np.flatnonzero(y_arr == 1)
    n_human = len(human_idx)
    if n_human == 0:
        raise ValueError("No human (label 0) rows in y.")
    n_ai = min(len(ai_idx), ai_per_human * n_human)
    rng = np.random.default_rng(random_state)
    ai_pick = rng.choice(ai_idx, size=n_ai, replace=False)
    keep = np.concatenate([human_idx, ai_pick])
    rng.shuffle(keep)
    return x[keep], y_arr[keep]


def features_on_gpu(x: np.ndarray):
    """
    Copy a feature matrix onto the GPU so XGBoost does not fall back to CPU data.

    Sparse input (the TF-IDF matrix) stays a float32 CSR matrix: densifying it
    would take several GB, and XGBoost moves CSR data to the GPU by itself.
    """
    if sp.issparse(x):
        return x.tocsr().astype(np.float32)

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
    groups: Optional[Sequence] = None,
) -> Tuple[XGBClassifier, Any]:
    """
    Tune and fit one XGBoost model; every model in the study goes through here.

    Without x_val / y_val this is the procedure in the paper: grid search with
    cv_folds-fold cross-validation on the training rows, then the winner is
    refit on all of them. Pass groups (one id per training row) so rows that
    belong together never straddle two folds. The score is ROC-AUC minus FPR.

    With x_val / y_val, hyperparameters are picked on the validation slice
    instead: each combo may grow up to n_estimators trees and stops when
    validation logloss has not improved for early_stopping_rounds rounds. A
    depth-1 model replaces the winner when its validation FPR is within half a
    point. The test slice is never used here.
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
            x_train, y_train, param_grid, cv_folds, random_state, device, use_cuda, groups
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
    groups: Optional[Sequence] = None,
) -> Tuple[XGBClassifier, GridSearchCV]:
    """
    Grid search with grouped, stratified k-fold CV, then refit on all train rows.

    Rows sharing a group id (passages of one essay, an original and its
    polished text) always sit in the same fold, so a fold's score is never
    inflated by a near-copy of a row it trained on.
    """
    if groups is None:
        raise ValueError(
            "Cross-validation needs groups (one id per training row) so related rows "
            "stay in the same fold."
        )
    groups = np.asarray(groups)
    if len(groups) != len(y_train):
        raise ValueError(f"groups length {len(groups)} != y_train length {len(y_train)}")
    x_fit = features_on_gpu(x_train) if use_cuda else x_train
    base = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        device=device,
        tree_method="hist",
        n_jobs=1,
        random_state=random_state,
    )
    cv = StratifiedGroupKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    search = GridSearchCV(
        base,
        param_grid,
        cv=cv,
        scoring=make_scorer(hybrid_cv_score, response_method="predict_proba"),
        n_jobs=1,
        verbose=1,
    )
    search.fit(x_fit, y_train, groups=groups)
    return search.best_estimator_, search


def select_on_validation(
    search: GridSearchCV,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    top_k: int = 3,
    random_state: int = 42,
    use_cuda: bool = True,
) -> Tuple[XGBClassifier, Dict[str, Any], pd.DataFrame]:
    """
    Compare the top cross-validated settings on the validation slice and keep the best.

    The top_k settings from the grid search are each fit on all train rows (the
    first one already is, by GridSearchCV's refit). The validation slice only
    chooses between them, using the same ROC-AUC minus FPR score as the CV;
    nothing is tuned or refit on it. Ties go to the better CV rank.

    Returns the chosen model, its params, and a table with one row per
    candidate (CV rank, params, CV mean/std, validation numbers, `selected`).
    """
    results = getattr(search, "cv_results_", {})
    if "params" not in results or not hasattr(search, "best_index_"):
        raise ValueError("Pass the GridSearchCV object returned by the cross-validated training path.")

    mean_scores = np.asarray(results["mean_test_score"], dtype=float)
    # Best setting first (its model is already refit), then the rest by CV score.
    rest = [i for i in np.argsort(-mean_scores, kind="stable") if i != search.best_index_]
    order = ([int(search.best_index_)] + [int(i) for i in rest])[: max(1, int(top_k))]

    device = "cuda" if use_cuda else "cpu"
    x_eval = features_on_gpu(x_val) if use_cuda else x_val
    y_eval = np.asarray(y_val)
    x_fit = None  # built lazily: only needed when a runner-up has to be refit

    models, rows = [], []
    for cv_rank, i in enumerate(order, start=1):
        params = dict(results["params"][i])
        if i == search.best_index_:
            model = search.best_estimator_
        else:
            if x_fit is None:
                x_fit = features_on_gpu(x_train) if use_cuda else x_train
            model = XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                device=device,
                tree_method="hist",
                n_jobs=1,
                random_state=random_state,
                **params,
            )
            model.fit(x_fit, y_train)
        proba = model.predict_proba(x_eval)[:, 1]
        report = classification_report_row(y_eval, proba)
        models.append((model, params))
        rows.append(
            {
                "cv_rank": cv_rank,
                **{f"param_{key}": value for key, value in params.items()},
                "cv_mean": float(mean_scores[i]),
                "cv_std": float(results["std_test_score"][i]),
                "val_roc_auc": report["roc_auc"],
                "val_fpr": report["fpr"],
                "val_score": float(report["roc_auc"] - report["fpr"]),
            }
        )

    table = pd.DataFrame(rows)
    chosen = int(np.argmax(table["val_score"].to_numpy()))  # first max = best CV rank on ties
    table["selected"] = np.arange(len(table)) == chosen
    model, params = models[chosen]
    print(
        f"Validation picked CV rank {chosen + 1} of {len(table)}: "
        f"score {table.loc[chosen, 'val_score']:.4f}, FPR {table.loc[chosen, 'val_fpr']:.3%}"
    )
    return model, params, table


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
