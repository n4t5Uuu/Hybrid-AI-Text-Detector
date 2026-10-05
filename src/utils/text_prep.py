"""
Last-mile text prep so human and AI rows reach the models in the same shape.

`combine_cleaned_datasets` uses `chunk_bawe_essays` to cut long BAWE essays into
passages that are as long as the AI texts. `feature_extraction.ipynb` uses
`strip_placeholders` right before spaCy and ELECTRA see the text.

This file sits outside the cleaning package on purpose: it only needs numpy
and pandas, so the GPU box can import it without the cleaning dependencies.
"""

import re

import numpy as np
import pandas as pd

# Matches [[CODE]] and the broken versions we have in the data: [[EQUATION] , [[[CODE]], [[G] ,
# and tags that lost their opening brackets (EQUATION]]). A closing ] is required so real
# text like "[[Theorem" or "[[0 1 0]" is left alone.
_PLACEHOLDER_RE = re.compile(
    r"\[{2,3}[A-Z]*\]{1,2}|\b(?:EQUATION|CODE|CITATION|COMPLEXITY|URL|MUSIC)\]{1,2}"
)
# Brackets left empty once a tag inside them is gone, like "()" or "( , )".
_EMPTY_BRACKETS_RE = re.compile(r"\(\s*[,;:]*\s*\)|\[\s*[,;:]*\s*\]")
_REPEATED_COMMA_RE = re.compile(r"([,;])(?:\s*[,;])+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([.,;:!?)\]])")
_SPACE_AFTER_OPEN_RE = re.compile(r"([(\[])\s+")
_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


def strip_placeholders(text):
    """
    Remove every [[TAG]] from the text and tidy what it leaves behind.

    Run this on both classes right before feature extraction. We do it for
    every row, not only the tagged ones, so spacing quirks cannot give away
    which source a text came from. Returns the cleaned string.
    """
    if not isinstance(text, str):
        return ""

    # Swap each tag for a space so neighbouring words never glue together.
    text = _PLACEHOLDER_RE.sub(" ", text)

    # Drop brackets that only held a tag, then fix commas and gaps around them.
    text = _EMPTY_BRACKETS_RE.sub(" ", text)
    text = _REPEATED_COMMA_RE.sub(r"\1", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    text = _SPACE_AFTER_OPEN_RE.sub(r"\1", text)
    return text.strip()


def count_words(text):
    """Count words the way the models see them: placeholders do not count."""
    if not isinstance(text, str):
        return 0
    return len(_PLACEHOLDER_RE.sub(" ", text).split())


def _split_long_sentence(sentence, max_words):
    """Cut a run-on 'sentence' into pieces of at most max_words words."""
    words = sentence.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def chunk_bawe_essays(
    bawe_df,
    target_word_counts,
    min_words=75,
    max_words=520,
    random_state=42,
):
    """
    Cut each BAWE essay into passages that are about as long as the AI texts.

    bawe_df needs id, text and subject columns (one row per essay). For each
    passage we draw a target length from target_word_counts (the AI word
    counts), then add whole sentences until we land as close to it as we can.
    A leftover tail shorter than min_words is dropped. Words inside [[TAG]]s
    do not count, so lengths still match after strip_placeholders.

    Returns one row per passage: id (the essay id), text, subject, chunk_idx.
    The combined table uses id as group_id so passages of one essay stay in
    the same split.
    """
    rng = np.random.default_rng(random_state)
    targets = np.clip(np.asarray(target_word_counts, dtype=int), min_words, max_words)

    rows = []
    for essay_id, text, subject in zip(bawe_df["id"], bawe_df["text"], bawe_df["subject"]):
        # Sentences first; a stray run-on sentence is cut into word windows.
        sentences = []
        for sentence in _SENTENCE_END_RE.split(str(text)):
            if count_words(sentence) > max_words:
                sentences.extend(_split_long_sentence(sentence, max_words))
            else:
                sentences.append(sentence)

        chunk_idx = 0
        current, current_words = [], 0
        goal = int(rng.choice(targets))

        for sentence in sentences:
            n_words = count_words(sentence)
            # Close the passage first if this sentence would overshoot by more
            # than stopping now undershoots.
            if current and (current_words + n_words - goal) > (goal - current_words):
                rows.append((essay_id, " ".join(current), subject, chunk_idx))
                chunk_idx += 1
                current, current_words = [], 0
                goal = int(rng.choice(targets))
            current.append(sentence)
            current_words += n_words

        if current and current_words >= min_words:
            rows.append((essay_id, " ".join(current), subject, chunk_idx))

    return pd.DataFrame(rows, columns=["id", "text", "subject", "chunk_idx"])
