"""What the feature extraction notebook imports: S, E, H, split, and training."""

from .electra_features import extract_electra_embeddings, load_electra, resolve_torch_device
from .late_fusion import fuse_spacy_electra, save_hybrid_features
from .spacy_features import (
    SPACY_FEATURE_NAMES,
    extract_spacy_matrix,
    features_from_doc,
    load_spacy_nlp,
    save_spacy_features,
)
from .data_splitting import (
    load_split_indices,
    save_split_artifacts,
    split_balance_table,
    stratified_train_val_test_split,
)
from .evaluate import classification_report_row, describe_fit, hybrid_cv_score
from .split_and_train import (
    features_on_gpu,
    fit_tfidf_on_train,
    require_cuda_for_training,
    save_hybrid_model,
    save_split_and_models,
    smoke_test_xgboost_cuda,
    train_xgboost_gpu,
    transform_tfidf,
)

__all__ = [
    "SPACY_FEATURE_NAMES",
    "extract_spacy_matrix",
    "features_from_doc",
    "load_spacy_nlp",
    "save_spacy_features",
    "extract_electra_embeddings",
    "load_electra",
    "resolve_torch_device",
    "fuse_spacy_electra",
    "save_hybrid_features",
    "stratified_train_val_test_split",
    "save_split_artifacts",
    "load_split_indices",
    "split_balance_table",
    "fit_tfidf_on_train",
    "transform_tfidf",
    "require_cuda_for_training",
    "smoke_test_xgboost_cuda",
    "features_on_gpu",
    "train_xgboost_gpu",
    "save_split_and_models",
    "save_hybrid_model",
    "classification_report_row",
    "hybrid_cv_score",
    "describe_fit",
]
