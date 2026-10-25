"""
Score one pasted text with the hybrid model, the same way the study scored its rows.

Pipeline (matches training): strip markdown → clean_pipeline → cut into passages
→ strip_placeholders → spaCy S + ELECTRA E → H = [S | E] → xgb_hybrid.json.
Long texts are cut into passages because the model was trained on passages
(about 200 words, never more than 520); the text's score is the word-weighted
mean of its passage scores.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import torch
import xgboost as xgb

from utils.cleaning import clean_markdown_formatting, clean_pipeline
from utils.features.electra_features import extract_electra_embeddings, load_electra
from utils.features.late_fusion import fuse_spacy_electra
from utils.features.spacy_features import SPACY_FEATURE_NAMES, extract_spacy_matrix, load_spacy_nlp
from utils.text_prep import chunk_bawe_essays, count_words, strip_placeholders

THRESHOLD = 0.50  # same decision threshold as Table 6
PASSAGE_TARGET_WORDS = 200  # about the median training passage
PASSAGE_MAX_WORDS = 520  # longest passage the model saw in training
MIN_TAIL_WORDS = 75  # a shorter last passage is merged into the one before it
MIN_PROSE_WORDS = 50  # below this the score is not reliable


def score_band(percent: float) -> str:
    """Interpretation bands from Table 4 of the paper."""
    if percent <= 20:
        return "Likely Human-Written"
    if percent >= 80:
        return "Highly Likely AI-Generated"
    return "Possible AI Assistance / Mixed Content"


def split_passages(cleaned: str) -> List[str]:
    """Cut cleaned text into training-sized passages at sentence boundaries."""
    if count_words(cleaned) <= PASSAGE_MAX_WORDS:
        return [cleaned]
    parts = chunk_bawe_essays(
        pd.DataFrame({"id": [0], "text": [cleaned], "subject": [""]}),
        target_word_counts=[PASSAGE_TARGET_WORDS],
        min_words=1,  # keep the tail; it is merged below if it is short
        max_words=PASSAGE_MAX_WORDS,
    )["text"].tolist()
    if len(parts) > 1 and count_words(parts[-1]) < MIN_TAIL_WORDS:
        parts[-2] = f"{parts[-2]} {parts.pop()}"
    return parts


@dataclass
class PassageScore:
    text: str
    word_count: int
    ai_probability: float  # 0..1


@dataclass
class DetectionResult:
    ai_probability: float  # 0..1, word-weighted over passages
    is_ai: bool
    band: str
    word_count: int
    passages: List[PassageScore]


class Detector:
    """Loads spaCy, ELECTRA and the hybrid XGBoost model once; scores texts on demand."""

    def __init__(self, model_path: Path):
        self.nlp = load_spacy_nlp(use_gpu=False)  # one text at a time: CPU spaCy is fast enough
        self.tokenizer, self.electra, self.device = load_electra(prefer_cuda=torch.cuda.is_available())
        self.model = xgb.XGBClassifier()
        self.model.load_model(str(model_path))
        self._lock = threading.Lock()  # spaCy and torch models are not meant for concurrent calls

    def predict(self, text: str) -> DetectionResult:
        cleaned = clean_pipeline(clean_markdown_formatting(text))
        passages = [strip_placeholders(p) for p in split_passages(cleaned)]
        passages = [p for p in passages if p]
        words = np.array([count_words(p) for p in passages], dtype=float)
        if words.sum() < MIN_PROSE_WORDS:
            raise ValueError(
                f"Not enough prose to analyse after removing code, equations and citations "
                f"({int(words.sum())} words; at least {MIN_PROSE_WORDS} needed)."
            )

        with self._lock:
            S = extract_spacy_matrix(passages, self.nlp, show_progress=False)
            E = extract_electra_embeddings(
                passages, self.tokenizer, self.electra, self.device, show_progress=False
            )
            H, _ = fuse_spacy_electra(S, E, SPACY_FEATURE_NAMES)
            probs = self.model.predict_proba(H)[:, 1]

        overall = float(np.average(probs, weights=words))
        return DetectionResult(
            ai_probability=overall,
            is_ai=overall >= THRESHOLD,
            band=score_band(round(overall * 100)),
            word_count=int(words.sum()),
            passages=[
                PassageScore(text=p, word_count=int(w), ai_probability=float(pr))
                for p, w, pr in zip(passages, words, probs)
            ],
        )
