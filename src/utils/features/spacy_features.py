"""
spaCy stats per essay — that's **S** in the thesis.

The feature extraction notebook runs this on the combined table, then fusion
pastes **S** next to **E** for each row (same essay order).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np
import pandas as pd
from tqdm import tqdm

FUNCTION_WORDS = frozenset(
    """
    a an the and or but if while although though because since until unless
    as when where whether after before during once than that this these those
    i me my we us our you your he him his she her it its they them their
    am is are was were be been being have has had do does did will would shall
    should may might must can could of in to for on at by from with about into
    through over under again further then once here there all each few more most
    other some such no nor not only own same so than too very s t can will just
    don should now
    """.split()
)

SPACY_FEATURE_NAMES: List[str] = [
    "ttr",
    "hapax_legomena_ratio",
    "avg_word_length",
    "function_word_ratio",
    "pos_noun_ratio",
    "pos_adj_ratio",
    "pos_verb_ratio",
    "pos_adv_ratio",
    "avg_dependency_length",
    "mean_parse_tree_depth",
]


def _token_depth(token) -> int:
    depth = 0
    current = token
    while current.head != current:
        depth += 1
        current = current.head
        if depth > 10_000:
            break
    return depth


def features_from_doc(doc) -> np.ndarray:
    """One essay → one **S** vector. Blank essays come back as all zeros."""
    words = [t for t in doc if t.is_alpha]
    n_words = len(words)
    if n_words == 0:
        return np.zeros(len(SPACY_FEATURE_NAMES), dtype=np.float32)

    # Lexical: how varied the wording is, word length, function-word share.
    lower = [t.lower_ for t in words]
    freq: dict[str, int] = {}
    for w in lower:
        freq[w] = freq.get(w, 0) + 1

    n_types = len(freq)
    ttr = n_types / n_words
    hapax = sum(1 for c in freq.values() if c == 1) / n_words
    avg_word_len = sum(len(w) for w in lower) / n_words
    fn = sum(1 for w in lower if w in FUNCTION_WORDS) / n_words

    # POS mix: share of nouns, verbs, adjectives, adverbs among content tags.
    pos_tokens = [t for t in doc if t.pos_ in {"NOUN", "VERB", "ADJ", "ADV"}]
    n_pos = len(pos_tokens) or 1
    pos_noun = sum(1 for t in pos_tokens if t.pos_ == "NOUN") / n_pos
    pos_adj = sum(1 for t in pos_tokens if t.pos_ == "ADJ") / n_pos
    pos_verb = sum(1 for t in pos_tokens if t.pos_ == "VERB") / n_pos
    pos_adv = sum(1 for t in pos_tokens if t.pos_ == "ADV") / n_pos

    # Syntax: how far tokens sit from their heads, average depth in the parse tree.
    dep_tokens = [t for t in doc if t.dep_ != "ROOT" and t.head != t]
    if dep_tokens:
        avg_dep = sum(abs(t.i - t.head.i) for t in dep_tokens) / len(dep_tokens)
    else:
        avg_dep = 0.0

    content = [t for t in doc if not t.is_space]
    if content:
        mean_depth = sum(_token_depth(t) for t in content) / len(content)
    else:
        mean_depth = 0.0

    return np.array(
        [
            ttr,
            hapax,
            avg_word_len,
            fn,
            pos_noun,
            pos_adj,
            pos_verb,
            pos_adv,
            avg_dep,
            mean_depth,
        ],
        dtype=np.float32,
    )


def load_spacy_nlp(model_name: str = "en_core_web_sm", use_gpu: bool = True):
    """Open spaCy; turn on the GPU when use_gpu is True."""
    import spacy

    if use_gpu:
        spacy.require_gpu()
    nlp = spacy.load(model_name, disable=["ner", "lemmatizer"])
    return nlp


def _normalize_text(text) -> str:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    s = str(text).strip()
    return s if s else ""


def extract_spacy_matrix(
    texts: Sequence,
    nlp,
    batch_size: int = 64,
    show_progress: bool = True,
) -> np.ndarray:
    """
    Run every essay through spaCy. Row i is always the same essay as texts[i].

    Empty or missing text stays zero so it still lines up with ELECTRA later.
    """
    n = len(texts)
    out = np.zeros((n, len(SPACY_FEATURE_NAMES)), dtype=np.float32)
    normalized = [_normalize_text(t) for t in texts]
    iterator: Iterable = normalized
    if show_progress:
        iterator = tqdm(normalized, total=n, desc="spaCy stylometric S")

    row = 0
    # nlp.pipe keeps batch order — row index still matches the original essay list.
    for doc in nlp.pipe(iterator, batch_size=batch_size):
        if not normalized[row]:
            out[row] = 0.0
        else:
            out[row] = features_from_doc(doc)
        row += 1
    return out


def save_spacy_features(
    texts: Sequence,
    labels: Sequence,
    sources: Sequence,
    subjects: Sequence,
    output_dir: Path,
    nlp,
    batch_size: int = 64,
) -> tuple[np.ndarray, Path]:
    """
    Save **S** with labels so you can spot-check in a table; also return the matrix.

    Fusion in the notebook uses the returned array, not the file on disk.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    s_matrix = extract_spacy_matrix(texts, nlp, batch_size=batch_size)

    # Column names for fusion / XGBoost; parquet adds labels for human checks.
    names_path = output_dir / "spacy_feature_names.json"
    names_path.write_text(json.dumps(SPACY_FEATURE_NAMES, indent=2), encoding="utf-8")

    frame = pd.DataFrame(s_matrix, columns=SPACY_FEATURE_NAMES)
    frame["label"] = labels
    frame["source"] = sources
    frame["subject"] = subjects
    parquet_path = output_dir / "spacy_features.parquet"
    frame.to_parquet(parquet_path, index=False)
    return s_matrix, parquet_path
