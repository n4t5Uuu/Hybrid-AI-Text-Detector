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
from .split_and_train import (
    fit_tfidf_on_train,
    save_split_and_models,
    stratified_train_val_test_split,
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
    "fit_tfidf_on_train",
    "transform_tfidf",
    "train_xgboost_gpu",
    "save_split_and_models",
]
