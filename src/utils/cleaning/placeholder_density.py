"""Placeholder density filters for dropping low-prose rows."""

import re

def placeholder_density(text):
    """
    This method is meant to remove the rows that have too many
    tokens on the cleaned data.
    """
    if not isinstance(text, str):
        return 0

    placeholder_count = len(re.findall(
        r'\[\[EQUATION\]\]|\[\[CODE\]\]|\[\[CITATION\]\]|\[\[COMPLEXITY\]\]|\[\[URL\]\]|\[\[FOREIGN\]\]|\[\[MUSIC\]\]',
        text
    ))
    word_count = len(re.findall(r'\b[a-zA-Z]{2,}\b', text))
    total = placeholder_count + word_count

    return placeholder_count / total if total > 0 else 0


def placeholder_density_windowed(text, window_chars=150, threshold=0.5):
    """
    Catches locally dense clusters of placeholders even inside one long
    run-on sentence (where the whole-document placeholder_density() can
    stay low because of lots of surrounding prose elsewhere). Slides a
    fixed-size character window across the text and flags True if ANY
    window exceeds the local density threshold — meant to be used
    alongside (not instead of) placeholder_density() when deciding
    whether to drop a row.
    """
    if not isinstance(text, str) or len(text) < window_chars:
        return False

    tag_pattern = re.compile(r'\[\[[A-Z]+\]\]')

    for start in range(0, len(text) - window_chars, window_chars // 2):
        window = text[start:start + window_chars]
        tag_char_len = sum(len(m.group()) for m in tag_pattern.finditer(window))
        if tag_char_len / len(window) >= threshold:
            return True

    return False
