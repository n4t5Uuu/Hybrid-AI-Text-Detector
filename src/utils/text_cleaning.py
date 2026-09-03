"""
Text cleaning utilities for the Hybrid AI Text Detector project.

This module provides functions to clean and preprocess academic text datasets
by removing or replacing mathematical notation, code snippets, citations, and
other non-prose elements with standardized placeholders.
"""

import re
import ast
import pandas as pd
from pathlib import Path
from tqdm.auto import tqdm
import IPython.display as ipd
from langdetect import detect, LangDetectException


# ==============================================================================
# Global Constants for Foreign Language Detection
# ==============================================================================

foreign_skip_counter = {"too_short": 0}

FOREIGN_DIACRITICS = set('àâäéèêëïîôöùûüÿçñáíóúü¿¡')
FRENCH_SPANISH_STOPWORDS = {
    'le', 'la', 'les', 'des', 'dans', 'avec', 'qui', 'une', 'du', 'aux',
    'los', 'las', 'muy', 'pero', 'también', 'más', 'está', 'entre', 'sobre',
    'porque', 'están', 'todo', 'toda', 'todos', 'merci', 'bonjour', 'vous',
    'que', 'ce', 'est', 'oui', 'gracias', 'hola', 'plaît', 'beaucoup',
    'votre', 'bibliothèque'
}
COMMON_LOANWORDS = {
    'cafe', 'café', 'resume', 'résumé', 'naive', 'naïve', 'cliche', 'cliché',
    'facade', 'façade', 'fiance', 'fiancé', 'fiancée', 'protege', 'protégé',
    'expose', 'exposé', 'déjà', 'deja', 'role', 'rôle', 'entree', 'entrée'
}

# Greek letters used as variables in physics/math leftovers (includes Φ for Faraday)
GREEK_CHARS = 'Σ∂ΦφϕθΘεδ∇ΔαβγλμπΩω∞'

# Trig names: require math context so English "sin" / "tan" / "sec" are not wiped
TRIG_PATTERN = (
    r'(?:arc(?:sin|cos|tan|sec|csc|cot)|a(?:sin|cos|tan)|'
    r'sinh|cosh|tanh|sin|cos|tan|sec|csc|cot)'
)


# ==============================================================================
# Core Cleaning Functions
# ==============================================================================

def clean_math_texts(text):
    """
        Cleans math equations, LaTeX expressions, and Unicode mathematical symbols from text
        by replacing them with [[EQUATION]] placeholders.
    """

    if not isinstance(text, str):
        return text

    # Normalize literal escaped newlines and citation markers
    text = text.replace('\\n', ' ')
    text = re.sub(r'\[\d+\]', '', text)

    # LaTeX environments
    text = re.sub(r'\\begin\{[a-zA-Z0-9\*]+\}.*?\\end\{[a-zA-Z0-9\*]+\}', ' [[EQUATION]] ', text, flags=re.DOTALL)

    # LaTeX block and display math
    text = re.sub(r'\$\$.*?\$\$', ' [[EQUATION]] ', text, flags=re.DOTALL)
    text = re.sub(r'\\\[.*?\\\]', ' [[EQUATION]] ', text, flags=re.DOTALL)

    # LaTeX inline math — require real math so $perseverance$ / $0.3 trillion ... $19.5
    # currency spans are not treated as equations.
    def _inline_math_replacer(m):
        inner = m.group(1).strip()
        if not inner:
            return m.group(0)
        words = re.findall(r'[A-Za-z]{3,}', inner)
        if len(words) >= 3:
            return m.group(0)
        # Currency/prose between two $: "$0.3 trillion in 1970 to $19.5"
        long_words = re.findall(r'[A-Za-z]{4,}', inner)
        if long_words and (' ' in inner) and '\\' not in inner:
            return m.group(0)
        has_math = bool(re.search(rf'[\\^_+\-*/=<>]|[0-9]|[{GREEK_CHARS}]', inner))
        is_short_id = bool(re.fullmatch(r'[A-Za-z]{1,2}', inner))
        if has_math or is_short_id:
            return ' [[EQUATION]] '
        return m.group(0)

    text = re.sub(r'\$([^\$\n]+)\$', _inline_math_replacer, text)
    text = re.sub(r'\\\((.*?)\\\)', ' [[EQUATION]] ', text)

    # Common LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+(\{.*?\})*', ' [[EQUATION]] ', text)

    # Integrals with bounds and differentials
    text = re.sub(r'[∮∫][₀-₉⁰-⁹\^]*[^\.\n]*?d[A-Za-z]+', ' [[EQUATION]] ', text)

    # Algebraic equations containing '=' or comparison operators.
    _EQ_TOKEN = r'[a-zA-Z0-9_\.]+'
    _EQ_OP = r'[\+\-\*/\^]'
    _EQ_EXPR = rf'{_EQ_TOKEN}(?:\s*{_EQ_OP}\s*{_EQ_TOKEN})*'
    text = re.sub(
        rf'\b{_EQ_EXPR}\s*(?:<=|>=|!=|==|=|<|>|≠|≤|≥|≈)\s*{_EQ_EXPR}',
        ' [[EQUATION]] ', text
    )

    # Exponents and derivatives — no bare parens in the token class (see
    # docstring above for why)
    text = re.sub(r'\b[a-zA-Z0-9]+\^[a-zA-Z0-9\+\-]+\b', ' [[EQUATION]] ', text)
    text = re.sub(
        rf'(?<![A-Za-z])d[{GREEK_CHARS}A-Za-z][A-Za-z0-9]*/d[A-Za-z]\b',
        ' [[EQUATION]] ', text
    )
    # Parenthesized derivatives: (mv)/dt, d(mv)/dt — no \b before '(' (space is non-word)
    text = re.sub(
        r'(?<![A-Za-z])d?\s*\((?![^)]*[A-Za-z]{3,})[^)]{1,20}\)\s*/\s*d[A-Za-z]\b',
        ' [[EQUATION]] ', text
    )
    # Short math assignments with unary minus: b = -5, c = 2 (not "year = 2020")
    text = re.sub(
        r'\b[A-Za-z]{1,3}\s*=\s*-?\d+(?:\.\d+)?\b',
        ' [[EQUATION]] ', text
    )

    # "n choose k" style combinatorics notation
    text = re.sub(r'\([a-zA-Z0-9\s\+\-]+choose[a-zA-Z0-9\s\+\-]+\)', '[[EQUATION]]', text)

    # Catches sentences that survived token-level cleaning but are still mostly fragments/placeholders
    cleaned_sentences = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    prev_was_equation = False

    for sent in sentences:
        placeholder_count = sent.count('[[EQUATION]]')
        non_placeholder_text = re.sub(r'\[\[EQUATION\]\]', '', sent)
        word_count = len(re.findall(r'[a-zA-Z]{3,}', non_placeholder_text))

        # If a sentence has 2+ placeholders and very few real words around them,
        # it's fragment soup, so we need to collapse to a single [[EQUATION]]
        is_fragment_heavy = placeholder_count >= 2 and word_count < 6

        if is_fragment_heavy or (placeholder_count >= 1 and word_count == 0):
            if not prev_was_equation:
                cleaned_sentences.append("[[EQUATION]]")
            prev_was_equation = True
        else:
            cleaned_sentences.append(sent)
            prev_was_equation = False

    text = ' '.join(cleaned_sentences)
    text = re.sub(r'(\[\[EQUATION\]\]\s*){2,}', '[[EQUATION]]', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def clean_bare_expressions(text):
    """
        Cleans up any remaining expressions that the clean_math_texts and clean_residual_math_noise
        didn't clean
    """

    if not isinstance(text, str):
        return text

    # Cleans up any factortials that are parenthesized first 
    # e.g. "(n-1)!"
    for _ in range(2):
        text = re.sub(r'\([^()]{1,30}\)!', ' [[EQUATION]] ', text)
        text = re.sub(r'\b[a-zA-Z0-9]+!', ' [[EQUATION]] ', text)

    # Cleans up the innermost balanced parenthetical expressions that are "pure math"
    paren_pattern = re.compile(r'\(([^()]{1,60})\)')

    paren_pattern = re.compile(r'\(([^()]{1,60})\)')

    def paren_replacer(m):
        content = m.group(1)
        has_math_content = bool(re.search(r'[\d\+\-\*/\^]', content)) or '[[EQUATION]]' in content
        if is_non_prose(content) and has_math_content:
            return ' [[EQUATION]] '
        return m.group(0)  # leave non-math parens (e.g. "(see below)") alone

    prev = None
    while prev != text:
        prev = text
        text = paren_pattern.sub(paren_replacer, text)

    # For the adjacent-placeholder implicait multiplication 
    # e.g. "(x+y)(x-y)"
    text = re.sub(r'(\[\[EQUATION\]\]\s*){2,}', '[[EQUATION]] ', text)

    # For cleaning up the Bare ASCII digit fractions
    # e.g. 1/2, 3/4 (which are distinct from unit-slash)
    # patterns that handles the units like "m/s" are handlded in clean_residual_math_noise
    text = re.sub(r'\b\d+\s*/\s*\d+\b', ' [[EQUATION]] ', text)

    # This merges a trailing component suffix directly onto a placeholder 
    # "[[EQUATION]]^2" -> "[[EQUATION]]"
    text = re.sub(r'\[\[EQUATION\]\]\s*\^\s*[a-zA-Z0-9\+\-]+', ' [[EQUATION]] ', text)

    # Merges a short leading number/variable + operator immediately before a placeholder
    # "4 * [[EQUATION]]" into one tag. This will loop so it can clean or absorb chained prefixes 
    # like "4 * 2 8 [[EQUATION]]" into one tag.
    for _ in range(2):
        text = re.sub(r'\b[a-zA-Z0-9]{1,3}\s*[\*/\^]\s*\[\[EQUATION\]\]', ' [[EQUATION]] ', text)

    # Merges a short trailing operator + number/variable right after a placeholder 
    # e.g. [[EQUATION]] * 2 and merges it into one tag
    for _ in range(2):
        text = re.sub(r'\[\[EQUATION\]\]\s*[\*/\^\+\-]\s*[a-zA-Z0-9]{1,3}\b(?!\w)', ' [[EQUATION]] ', text)

    text = re.sub(r'(\[\[EQUATION\]\]\s*){2,}', '[[EQUATION]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def clean_residual_math_noise(text):
    """
        Final mop-up pass for math-heavy content that survives the main
        clean_math_texts regex pipeline: standalone Unicode math symbols,
        Pascal's-triangle-style bare numeric sequences, ASCII lattice/diagram
        art, and orphaned brackets left over from earlier substitutions.
        Run this AFTER clean_math_texts in the pipeline.
    """
    if not isinstance(text, str):
        return text

    # GREEK now includes ∞ (infinity) and Φ/φ (Faraday flux).
    GREEK = GREEK_CHARS

    # For catching functions like f(x), g(x), etc
    for _ in range(2):
        text = re.sub(
            r'\b[a-zA-Z]{1,2}\d{0,2}\([a-zA-Z0-9,\s\+\-\*/\^\.]*\)',
            ' [[EQUATION]] ', text
        )

    # Units with exponents
    text = re.sub(r'\b[a-zA-Z]+(?:\*[a-zA-Z]+)?/[a-zA-Z]+[\^²³]*\d*\b', ' [[EQUATION]] ', text)

    # For absolute values
    text = re.sub(r'\|[a-zA-Z0-9\+\-\*/\^\.,\s]{1,40}\|', ' [[EQUATION]] ', text)

    # For replacing square roots
    text = re.sub(r'√\s*\(?[a-zA-Z0-9\+\-\*/\^\.,\s]*\)?', ' [[EQUATION]] ', text)

    # For the Unicode of fraction and superscript characters attached to a term
    text = re.sub(r'[a-zA-Z0-9\)]*[½⅓¼¾⅔⅕⅖⅗][a-zA-Z0-9\(]*', ' [[EQUATION]] ', text)
    text = re.sub(r'\b[a-zA-Z0-9\)]+[²³¹⁰⁴⁵⁶⁷⁸⁹]+', ' [[EQUATION]] ', text)
    # Superscript / subscript glued to an already-inserted tag: [[EQUATION]]² / 2, ²h/3
    text = re.sub(
        r'\[\[EQUATION\]\]\s*[A-Za-z]?[²³¹⁰⁴⁵⁶⁷⁸⁹]+[A-Za-z0-9]*(?:\s*/\s*\d+)?',
        ' [[EQUATION]] ', text
    )
    text = re.sub(
        r'\[\[EQUATION\]\]\s*[₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₙ]+',
        ' [[EQUATION]] ', text
    )

    # Plus-minus: ±b, ± 1
    text = re.sub(r'±\s*[a-zA-Z0-9\.\(\)]+', ' [[EQUATION]] ', text)

    # Greek-letter variables and comparison chains (now also catches ∞,
    # e.g. "B=∞", "distance = ∞")
    text = re.sub(
        rf'(?<![a-zA-Z0-9])[{GREEK}][a-zA-Z0-9]*(?:\s*(?:[+\-*/^=<>]|<=|>=)\s*(?:(?<![a-zA-Z0-9])[{GREEK}]|[a-zA-Z0-9])[a-zA-Z0-9\.]*)*',
        ' [[EQUATION]] ', text
    )

    # Partial-derivative fraction pattern: [[EQUATION]]f1/[[EQUATION]]x
    text = re.sub(r'\[\[EQUATION\]\]\s*[a-zA-Z0-9]*\s*/\s*\[\[EQUATION\]\]\s*[a-zA-Z0-9]*', ' [[EQUATION]] ', text)

    # Stepped-subscript variables: xn+1, yn+1, zn+1, x0, y0
    text = re.sub(r'\b(?:x|y|z)(?:n\+1|n-1|0)\b', ' [[EQUATION]] ', text)
    text = re.sub(r'\b[a-zA-Z]n\+1\b|\b[a-zA-Z]n-1\b', ' [[EQUATION]] ', text)

    # Bracket-wrapped variable/component
    text = re.sub(
        rf'(?<!\[)\[(?:[{GREEK}][a-zA-Z0-9]*|[a-zA-Z]\d)(?:[\s,][{GREEK}a-zA-Z0-9]*)*\](?!\])',
        ' [[EQUATION]] ', text
    )

    # Bare numeric sequences
    text = re.sub(r'(?:\b\d+\b[\s,]+){3,}\b\d+\b', ' [[EQUATION]] ', text)

    # Orphaned brackets/parenthesis left behind
    for _ in range(3):
        text = re.sub(r'\([^()]*\[\[EQUATION\]\][^()]*\)', ' [[EQUATION]] ', text)
        text = re.sub(r'(?<!\[)\[[^\[\]]*\[\[EQUATION\]\][^\[\]]*\](?!\])', ' [[EQUATION]] ', text)

    # Merge a leftover math-function-name letter sitting right before a placeholder
    text = re.sub(r'\b[fghFGH]\d{0,2}\s*\[\[EQUATION\]\]', ' [[EQUATION]] ', text)

    # Stray single bracket immediately touching our own [[ / ]] delimiters
    text = re.sub(r'\[\s*(?=\[\[EQUATION\]\])', '', text)
    text = re.sub(r'(?<=\[\[EQUATION\]\])\s*\]', '', text)

    # NEW: stray angle brackets immediately touching our own delimiters —
    # leftover from pseudocode block markers like "< Let's run ... >" that
    # got partially eaten by clean_math_texts' comparison-operator regex,
    # same failure mode that originally broke <COMPLEXITY>/<CITATION>.
    text = re.sub(r'<\s*(?=\[\[EQUATION\]\])', '', text)
    text = re.sub(r'(?<=\[\[EQUATION\]\])\s*>', '', text)

    # Repeat after Greek: π²h → [[EQUATION]] ²h
    text = re.sub(
        r'\[\[EQUATION\]\]\s*[A-Za-z]?[²³¹⁰⁴⁵⁶⁷⁸⁹]+[A-Za-z0-9]*(?:\s*/\s*\d+)?',
        ' [[EQUATION]] ', text
    )
    text = re.sub(
        r'\[\[EQUATION\]\]\s*[₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₙ]+',
        ' [[EQUATION]] ', text
    )

    # Consolidate and clean whitespace
    text = re.sub(r'(\[\[EQUATION\]\]\s*){2,}', '[[EQUATION]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def is_non_prose(fragment,  tag_names=('EQUATION', 'CODE', 'CITATION', 'COMPLEXITY', 'URL', 'FOREIGN', 'MUSIC')):

    """
        A fragment counts as "pure math" (non-prose) if it has no run of
        3+ letters forming a real word — the tag names themselves (e.g.
        "EQUATION") are excluded from this check first, so a fragment
        that's just an already-inserted placeholder doesn't accidentally
        fail the check because of its own tag text.
    """

    stripped = fragment
    for name in tag_names:
        stripped = stripped.replace(f'[[{name}]]', '')
    return not re.search(r'[A-Za-z]{3,}', stripped)

def clean_pseudocode_and_diagrams(text):
    """
        Catches un-backticked code and text-diagram notation that
        clean_code_texts (which only looks for markdown fences/backticks)
        misses.
    """
    if not isinstance(text, str):
        return text

    # [Dashboard] [[EQUATION]] -- Fuel Gauge (diagram node split by a math tag)
    text = re.sub(
        r'\[[^\[\]]{1,30}\]\s*\[\[EQUATION\]\]\s*[|\->]{2,}\s*[A-Za-z][A-Za-z0-9 ]{0,40}',
        ' [[CODE]] ', text
    )
    # 2+ [node] groups — connector must include | - > / so "[1] [2]" citations stay
    text = re.sub(
        r'\[[^\[\]]{1,30}\](?:[ \t]*[|/>\-][ \t|/>\-]{0,9}\[[^\[\]]{1,30}\])+',
        ' [[CODE]] ', text
    )

    # Class / abstract-class blocks with curly braces
    text = re.sub(
        r'\b(?:abstract\s+)?class\s+\w+(?:\s+extends\s+\w+)?\s*\{[^{}]*\}',
        ' [[CODE]] ', text
    )
    # Any remaining generic curly-brace block
    text = re.sub(r'\{[^{}]{1,200}\}', ' [[CODE]] ', text)

    # Dot-notation method calls: car.accelerate(), object.method(args)
    text = re.sub(r'\b[a-zA-Z_]\w*\.[a-zA-Z_]\w*\([a-zA-Z0-9_,\s\'"]*\)', ' [[CODE]] ', text)

    # Python def/return statements
    text = re.sub(r'\bdef\s+\w+\([^)]*\)\s*:', ' [[CODE]] ', text)
    text = re.sub(r'\breturn\s+[a-zA-Z0-9_\*\+\-/\(\)\s\.]{1,40}(?=[.,:;]|$)', ' [[CODE]] ', text)

    # Named function calls (3+ letter identifiers, e.g. factorial(5),
    # factorial(n-1)) 
    text = re.sub(r'\b[a-z_][a-zA-Z0-9_]{2,}\([a-zA-Z0-9_,\s\+\-\*/\.]*\)', ' [[CODE]] ', text)

    # Common cross-language keywords signaling a code line (Java/C/C++/JS)
    text = re.sub(
        r'\b(?:public|private|protected|void|int|float|double|boolean|const|let|var|function)\b[^.!?]{0,60}?[;{]',
        ' [[CODE]] ', text
    )

    text = re.sub(r'(\[\[CODE\]\]\s*){2,}', '[[CODE]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def clean_code_texts(text):
    """
        Cleans code blocks and inline code snippets from text by replacing them
        with [[CODE]] placeholders.
    """
    if not isinstance(text, str):
        return text

    # Replace markdown fenced code blocks with [[CODE]] instead of <CODE>
    text = re.sub(r'```[a-zA-Z0-9_\+\#-]*\n?[\s\S]*?```', ' [[CODE]] ', text)

    # Replace inline code snippets
    text = re.sub(r'`[^`\n]+`', ' [[CODE]] ', text)

    text = re.sub(r'(\[\[CODE\]\]\s*){2,}', '[[CODE]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def clean_complexity_notation(text):
    """
        Cleans the rows that has any Big-O notation in the dataset
    """

    if not isinstance(text, str):
        return text

    # Big-O, Big-Theta, Big-Omega notation: O(n), O(log n), O(n^2), Θ(n), Ω(n log n)
    # Requires the letter to be standalone (not preceded by another letter) to avoid
    # false matches like "info(x)" or "to(n)" — also drops lowercase 'o' since it's
    # too ambiguous with common English words even with the lookbehind guard.
    text = re.sub(r'(?<![a-zA-Z])[OΘΩ]\(\s*[a-zA-Z0-9\s\^\+\-\*/,]*\)', ' [[COMPLEXITY]] ', text)

    text = re.sub(r'(\[\[COMPLEXITY\]\]\s*){2,}', '[[COMPLEXITY]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def clean_list_numbering(text):
    """
        Cleans texts that has any numbering in it
        e.g. 1. 2. ...
    """

    if not isinstance(text, str):
        return text

    # Numbered list markers: "1.", "2.", "\n3."
    text = re.sub(r'(?:^|(?<=[\s:;\.]))\d{1,2}\.\s+(?=[A-Za-z])', ' ', text)

    # Letter list markers: only at start, after newline, or after colon —
    # not after operators (avoids "a + b. Step 2" → "a + Step 2")
    text = re.sub(r'(?:^|(?<=\n)|(?<=:))\s*[a-zA-Z][\.\)]\s+(?=[A-Za-z0-9])', ' ', text)

    # Roman Numerals list markers
    text = re.sub(r'(?:^|(?<=[\s:;\.]))(?:i{1,3}|iv|v|vi{0,3}|ix|x)[\.\)]\s+', ' ', text, flags=re.IGNORECASE)

    # Dash/bullet markers: "- Puts more money...", "\n- Allows workers..."
    text = re.sub(r'(?:^|\n)\s*-\s+', ' ', text)

    # Cleans up any whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def clean_citations(text):
    """
        Replaces any citations whether intext to [[CITATION]]
    """
    if not isinstance(text, str):
        return text

    # Bracketed numeric citations: [1], [12], [1,2]
    text = re.sub(r'\[\d+(,\s*\d+)*\]', ' [[CITATION]] ', text)

    # Parenthetical citations: (Smith, 2020), (Smith et al., 2020), (Smith & Jones, 2020),
    # (Smith, 2020; Lee, 2019), (Smith 2020) — comma optional, semicolon-joined multiples
    text = re.sub(
        r'\([A-Z][a-zA-Z\.\s,&]*?(?:et al\.)?\s*,?\s*\d{4}[a-z]?(?:\s*;\s*[A-Z][a-zA-Z\.\s,&]*?\d{4}[a-z]?)*\)',
        ' [[CITATION]] ', text
    )

    # Narrative citations: "Smith (2020)", "Smith et al. (2020)"
    text = re.sub(r'\b[A-Z][a-zA-Z]+(?:\set al\.)?\s\(\d{4}[a-z]?\)', ' [[CITATION]] ', text)

    text = re.sub(r'(\[\[CITATION\]\]\s*){2,}', '[[CITATION]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def clean_url(text):
    """
        Replaces URLs (even with or without a preceding hyperlink label) with
        [[URL]] placeholders.
    """
    if not isinstance(text, str):
        return text

    # Standard http(s):// URLs
    text = re.sub(r'https?://\S+', ' [[URL]] ', text)

    # www.-prefixed URLs without a scheme
    text = re.sub(r'\bwww\.\S+', ' [[URL]] ', text)

    text = re.sub(r'(\[\[URL\]\]\s*){2,}', '[[URL]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def strip_reference_list(text):
    """Cuts off everything from the first 'Sources:' / 'References' """

    match = re.search(r'\n?(Sources|References|Bibliography):', text, flags=re.IGNORECASE)

    if match:
        return text[:match.start()].strip()

    return text

def clean_music_notation(text):
    """
        Replaces musical note/chord progression notation (e.g. C-G-D-A,
        C3-G3-D4-A4, F#-Bb-D) with [[MUSIC]] placeholders.
    """
    if not isinstance(text, str):
        return text

    note = r'[A-G](?:#|b)?\d?'
    text = re.sub(rf'\b{note}(?:-{note}){{1,}}\b', ' [[MUSIC]] ', text)

    text = re.sub(r'(\[\[MUSIC\]\]\s*){2,}', '[[MUSIC]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def merge_continuous_equations(text, tag='[[EQUATION]]'):
    """
        Merges adjacent placeholders separated by operators, short math,
        trig names, or (for CODE) return/returns. Pair pattern is restricted
        to math/code connectors so a failed prose pair cannot skip a later
        [[EQUATION]] + [[EQUATION]] chain.
    """

    if not isinstance(text, str):
        return text

    esc = re.escape(tag)
    if tag == '[[CODE]]':
        conn = r'(?:\s*(?:[\+\-\*/×÷=]|returns?)\s*)+'
    else:
        conn = (
            r'(?:\s*(?:'
            r'[\+\-\*/×÷=±]|'
            r'\d+(?:\.\d+)?|'
            rf'{TRIG_PATTERN}|'
            rf'd[{GREEK_CHARS}A-Za-z][A-Za-z0-9]*/d[A-Za-z]|'
            r'2a|4ac|4a|-b|bx|ac|bc|cx|ax|ab|'
            r'[-−][Nn]|'
            r'[²³¹⁰⁴⁵⁶⁷⁸⁹]+|'
            r'kg|m/s'
            r')\s*)+'
        )
    pair = re.compile(esc + conn + esc, re.IGNORECASE)

    prev = None
    while prev != text:
        prev = text
        text = pair.sub(f' {tag} ', text)

    text = re.sub(r'\s+', ' ', text).strip()
    return text


def mop_up_leftover_math_and_code(text):
    """
        Folds leftover math/code fragments that sit next to already-inserted
        placeholders: trig, dΦ/dt, both sides of '=', ±, 2a/4ac, x+c tails,
        named quantities, (xn, yn, zn), unit products, CODE sandwiches,
        and CODE return/operator tails.
        Run LAST in clean_pipeline, then merge again.
    """
    if not isinstance(text, str):
        return text

    EQ = r'\[\[EQUATION\]\]'
    CODE = r'\[\[CODE\]\]'
    OPS = r'[\+\-\*/×÷]'
    MATH_ATOM = (
        rf'(?:{EQ}|[{GREEK_CHARS}A-Za-z]\d{{0,2}}|\d+[abcxyzmnr]{{1,3}}|'
        rf'\d+(?:\.\d+)?|[-−][A-Za-z0-9]+|d[{GREEK_CHARS}A-Za-z][A-Za-z0-9]*/d[A-Za-z])'
    )

    # Trig in math context only (next to tag, '(', or '=')
    text = re.sub(
        rf'\b{TRIG_PATTERN}\s*(?={EQ}|\()',
        ' [[EQUATION]] ', text, flags=re.IGNORECASE
    )
    text = re.sub(
        rf'(?<={EQ})\s*{TRIG_PATTERN}\b',
        ' [[EQUATION]] ', text, flags=re.IGNORECASE
    )
    text = re.sub(
        rf'\b{TRIG_PATTERN}\s*=',
        ' [[EQUATION]] =', text, flags=re.IGNORECASE
    )
    # Glued trig: cosθ, cos30° (not "cosine" / "costs")
    text = re.sub(
        rf'\b{TRIG_PATTERN}(?:[{GREEK_CHARS}]|\d+°?)',
        ' [[EQUATION]] ', text, flags=re.IGNORECASE
    )
    text = re.sub(rf'{EQ}\s*\d+\s*°', ' [[EQUATION]] ', text)

    # Faraday-style derivatives, optional -N prefix
    text = re.sub(
        rf'[-−]?\s*(?:[Nn]\s+)?d[{GREEK_CHARS}A-Za-z][A-Za-z0-9]*/d[A-Za-z]\b',
        ' [[EQUATION]] ', text
    )
    text = re.sub(
        rf'[-−]?\s*[Nn]\s*\*?\s*d[{GREEK_CHARS}A-Za-z]/d[A-Za-z]\b',
        ' [[EQUATION]] ', text
    )

    # Both sides of '=' including [[EQUATION]] = 0 / 0.03
    for _ in range(5):
        text = re.sub(
            rf'{EQ}\s*=\s*(?:{EQ}|\d+(?:\.\d+)?|{MATH_ATOM})(?:\s*{OPS}\s*(?:{EQ}|{MATH_ATOM}))*',
            ' [[EQUATION]] ', text
        )
        text = re.sub(
            rf'(?:{MATH_ATOM}|[A-Za-z]{{1,4}})\s*=\s*[-−]?\s*{EQ}',
            ' [[EQUATION]] ', text
        )
        text = re.sub(rf'{EQ}\s*=\s*[-−]\s*{EQ}', ' [[EQUATION]] ', text)
        text = re.sub(rf'\|\s*{EQ}\s*\|', ' [[EQUATION]] ', text)
        text = re.sub(rf'{EQ}\s*=\s*\|', ' [[EQUATION]] ', text)

    # Single-letter (or short) term glued to a tag by an operator: x + [[EQUATION]]
    text = re.sub(rf'\b[A-Za-z]\d{{0,2}}\s*{OPS}\s*{EQ}', ' [[EQUATION]] ', text)
    text = re.sub(rf'{EQ}\s*{OPS}\s*[A-Za-z]\d{{0,2}}\b', ' [[EQUATION]] ', text)
    text = re.sub(r'\+/-', ' [[EQUATION]] ', text)

    # Algebraic coefficients next to tags or slash (not every "2x" in prose)
    text = re.sub(rf'{EQ}\s*/\s*\d+[abcxyz]{{1,3}}\b', ' [[EQUATION]] ', text)
    text = re.sub(rf'\b[abcxyz]/\d+[abcxyz]{{1,3}}\b', ' [[EQUATION]] ', text)
    text = re.sub(r'/\s*\d+[abcxyz]{1,3}\b', ' [[EQUATION]] ', text)
    text = re.sub(r'\[-b\b', ' [[EQUATION]] ', text)
    text = re.sub(rf'(?:{EQ}\s*[±]?\s*|\b[±]\s*)-b\b', ' [[EQUATION]] ', text)
    text = re.sub(
        rf'(?<=\[\[EQUATION\]\] )\d+[abcxyz]{{1,3}}\b|\b\d+[abcxyz]{{1,3}}\b(?=\s*(?:{EQ}|[±/]))',
        ' [[EQUATION]] ', text
    )

    # Coordinate tuples used as Newton/Jacobian points
    text = re.sub(r'\(\s*[xyz]n(?:\s*,\s*[xyz]n)+\s*\)', ' [[EQUATION]] ', text)

    # Indexed math functions f1, f2, f3 (not "F1 score")
    text = re.sub(r'\bf[1-9](?:\s*,\s*f[1-9])+\b', ' [[EQUATION]] ', text)
    text = re.sub(
        rf'(?:{EQ}|{CODE})\s*,?\s*\bf[1-9]\b|\bf[1-9]\b\s*(?:{EQ}|{CODE})',
        ' [[EQUATION]] ', text
    )

    # Dimension / unit products: require a leading number so "form" / "is" are not units
    text = re.sub(
        r'\b\d+\s*(?:cm|mm|m|kg|km|s)\s*[×x]\s*\d+'
        r'(?:\s*(?:cm|mm|m|kg|km|s))?'
        r'(?:\s*[×x]\s*\d+(?:\s*(?:cm|mm|m|kg|km|s))?)*',
        ' [[EQUATION]] ', text, flags=re.IGNORECASE
    )
    text = re.sub(
        rf'{EQ}(?:\s*(?:cm|mm|m))?(?:\s*[×x]\s*\d+(?:\s*(?:cm|mm|m))?)+\s*(?:{EQ})?',
        ' [[EQUATION]] ', text, flags=re.IGNORECASE
    )

    # CODE: return/returns and operators around tags
    text = re.sub(rf'\breturns?\s+{CODE}', ' [[CODE]] ', text, flags=re.IGNORECASE)
    text = re.sub(rf'{CODE}\s*{OPS}\s*{CODE}', ' [[CODE]] ', text)
    text = re.sub(rf'{CODE}\s+returns\s+{CODE}', ' [[CODE]] ', text, flags=re.IGNORECASE)

    # Named quantities: Mass (m) = 1,500 kg, Velocity (v) = 20 [[EQUATION]]
    _named_qty = (
        rf'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*\([A-Za-z]{{1,3}}\)\s*=\s*'
        rf'(?:-?[\d,]+(?:\.\d+)?(?:\s*(?:kg|g|cm|mm|km|mg|ms|mol|Hz|Pa|kJ|J|N|W|K|V|A))?'
        rf'(?:\s*{EQ})?|{EQ})'
    )
    text = re.sub(_named_qty, ' [[EQUATION]] ', text)
    # Joined givens: [[EQUATION]] - [[EQUATION]] already merges; also "qty - Name (x) ="
    text = re.sub(
        rf'{EQ}\s*[-−]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*\([A-Za-z]{{1,3}}\)\s*=',
        ' [[EQUATION]] ', text
    )

    # Algebra tails next to tags — require an operator (never a lone letter).
    # Longer pattern first so "a [[EQUATION]] b + ac" does not leave a leading "a".
    text = re.sub(
        rf'\b[A-Za-z]\s*{EQ}\s*[A-Za-z]{{1,3}}\s*{OPS}\s*[A-Za-z]{{1,3}}\b',
        ' [[EQUATION]] ', text
    )
    text = re.sub(
        rf'{EQ}\s*[A-Za-z]{{1,3}}\s*{OPS}\s*[A-Za-z]{{1,3}}\b',
        ' [[EQUATION]] ', text
    )
    text = re.sub(
        rf'{EQ}\s*{OPS}\s*[A-Za-z]{{1,3}}\s*=\s*-?[A-Za-z0-9]+\b',
        ' [[EQUATION]] ', text
    )

    # Leftover differential atom: [[EQUATION]] d Where v is
    text = re.sub(rf'{EQ}\s+d\s+(?=[Ww]here\b)', ' [[EQUATION]] ', text)
    text = re.sub(rf'{EQ}\s+d\s*/\s*d[A-Za-z]\b', ' [[EQUATION]] ', text)
    text = re.sub(
        rf'{EQ}\s+\((?![^)]*[A-Za-z]{{3,}})[^)]{{0,20}}\)\s*/\s*d[A-Za-z]\b',
        ' [[EQUATION]] ', text
    )
    text = re.sub(
        r'(?<![A-Za-z])d?\s*\((?![^)]*[A-Za-z]{3,})[^)]{1,20}\)\s*/\s*d[A-Za-z]\b',
        ' [[EQUATION]] ', text
    )

    # Superscript tails after tags (incl. ²h, b², leftover h/3 from π²h/3)
    text = re.sub(
        rf'{EQ}\s*[A-Za-z]?[²³¹⁰⁴⁵⁶⁷⁸⁹]+[A-Za-z0-9]*(?:\s*/\s*\d+)?',
        ' [[EQUATION]] ', text
    )
    text = re.sub(rf'{EQ}\s*[A-Za-z]/\d+\b', ' [[EQUATION]] ', text)

    # [[EQUATION]] / 2 and comma-grouped leftovers: [[EQUATION]] ,000 J
    text = re.sub(rf'{EQ}\s*/\s*\d+\b', ' [[EQUATION]] ', text)
    text = re.sub(
        rf'{EQ}\s*,\d{{3}}(?:\s*(?:kJ|kg|cm|mm|km|J|N|W|m|s))?\b',
        ' [[EQUATION]] ', text
    )

    # Summation next to a tag only
    text = re.sub(rf'\bsum\s+(?:from\s+)?(?={EQ})', ' [[EQUATION]] ', text, flags=re.IGNORECASE)
    text = re.sub(rf'(?<={EQ})\s*sum\b', ' [[EQUATION]] ', text, flags=re.IGNORECASE)

    # Debugging walkthrough sandwich — not a lone CODE beside a lone EQUATION
    for _ in range(3):
        text = re.sub(rf'{CODE}\s*{EQ}\s*{CODE}', ' [[CODE]] ', text)

    text = re.sub(r'(\[\[EQUATION\]\]\s*){2,}', '[[EQUATION]] ', text)
    text = re.sub(r'(\[\[CODE\]\]\s*){2,}', '[[CODE]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_code_assignments(text):
    """
        Replaces code-style numeric assignments (num = -1) when they sit next
        to [[CODE]] or iteration/condition keywords — not algebraic x = -3.
    """
    if not isinstance(text, str):
        return text

    text = re.sub(
        r'\b(?:Iteration\s+\d+:\s*)?[A-Za-z_][A-Za-z0-9_]*\s*=\s*-?\d+\s*,\s*condition(?:\s+(?:false|true))?\b',
        ' [[CODE]] ', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'(?:\[\[CODE\]\]\s*[,:]?\s*)[A-Za-z_][A-Za-z0-9_]*\s*=\s*-?\d+\b',
        ' [[CODE]] ', text
    )
    text = re.sub(
        r'\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*-?\d+\b(?=\s*,\s*(?:condition|true|false))',
        ' [[CODE]] ', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'(?i)(?:initialized to\s+)\d+',
        'initialized to [[CODE]]', text
    )

    text = re.sub(r'(\[\[CODE\]\]\s*){2,}', '[[CODE]] ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_academic_content(prompt="", text=""):
    """
        Returns False when the prompt (or stage-direction markers in either
        field) signals creative, fictional, commercial, or non-academic work.
        Creative keywords are matched on the prompt only so an academic
        response that happens to say "vivid scene" does not drop the row.
    """

    prompt_l = str(prompt).lower()
    combined = prompt_l + " " + str(text).lower()

    creative_keywords = [
        'script', 'commercial', 'advertisement', 'ad script', 'screenplay',
        'short story', 'novel', 'fairy tale', 'fairytale',
        'poem', 'poetry', 'lyrics', 'song', 'monologue', 'dialogue between',
        'playwright', 'haiku', 'sonnet', 'screenwriter', 'broadway', 'fanfiction',
        'imagine you are', 'shapeshift', 'shapeshifting', 'roleplay', 'role-play',
        'pretend you are', 'pretend that you are', 'pretend to be',
        'you wake up as',
        'from the perspective of a',
        'paint the vivid picture', 'paint a vivid picture', 'vivid picture of',
        'vivid scenes', 'vivid scene', 'in vivid detail',
        'describing in vivid detail', 'explore the senses',
        'sensory-rich', 'sensory rich', 'leave out function words',
        'run with passion', 'express yourself freely',
        'imagine yourself as', 'imagine discovering', 'imagine walking',
        'imagine interacting', 'in first person', 'fight scene',
        'fantasy tale', 'whimsical tale', 'heartwarming tale',
        'crash landed', 'blank canvas', 'lyrical passage',
        'motivational essay', 'action thriller', 'compose a piano sonata',
        'elderly elephant', 'typical day in the life',
        'epic battle', 'describe in vivid detail',
        "captivating the reader's imagination", 'captivate the reader',
        'lore behind', 'board game', 'video game',
        # Fiction / scene writing
        'magical girl anime', 'giant robots defending',
        'slice-of-life scene', 'describe an original anime',
        'original anime plot', 'write a scene where',
        'favorite anime', 'emerald green dragon',
        'unknown land of wonder and magic', 'climactic battle scene',
        "wizard's tale", 'owl named archimedes',
        'surrealist painting', 'dreamlike symbols',
        'movie scenes from three', 'psychological thriller movie',
        'iconic horror movie scene', 'film noir crime drama',
        'day-in-the-life narrative', 'walk a mile in the paws',
        'time travels from a rural farm pond',
        'whimsical design',
        # Animal / nature narrative (not expository biology)
        'stroll through the wildlife sanctuary',
        'walk through a farm and describe',
        'observe the behavior of an elephant enclosure',
        'observe the habits and personalities of various animals',
        # Sports drill / performance (not coaching essays)
        'practice your field goal', 'practice your dribbling',
        'run fast like the wind', 'shoot for the basket',
        'perform soccer tricks', 'throw three strike pitches',
        'at your mark, get set, leap',
        # Compose music (not music-history essays)
        'compose a classical music piece in the style of',
        'generate a three-part symphony',
        'compose a symphony movement that captures',
    ]

    if any(kw in prompt_l for kw in creative_keywords):
        return False

    # Prompt-only regex for creative framing without catching analysis essays
    prompt_patterns = [
        r'\bdescribe an original (?:anime|scene)\b',
        r'\bwrite a (?:scene|plot summary of one episode)\b',
        r'\bfrom the perspective of the farm\'s\b',
        r'\bnarrate a day in their journey\b',
        r'\bcompose a (?:musical composition|fable)\b',
    ]
    if any(re.search(p, prompt_l) for p in prompt_patterns):
        return False

    # Stage Direction & Script Structural Markers, plus letter/email
    script_patterns = [
        r'\[visual:', r'\[audio:', r'\[music', r'\[sfx:', r'\[scene',
        r'\[camera', r'\[upbeat', r'\[fade', r'\bnarrator:', r'\bint\.\s', r'\bext\.\s',
        r'\bdear\s+[a-z]+,', r'\bsincerely,', r'\byours\s+sincerely,',
        r'\bbest\s+regards,', r'\bwarm\s+regards,', r'\bkind\s+regards,',
        r'\byours\s+truly,', r'\bsubject:\s'
    ]

    if any(re.search(pattern, combined) for pattern in script_patterns):
        return False

    return True


def contains_foreign_language(text):
    """
        Returns True if ANY foreign-language content is detected anywhere
        in the text — non-Latin script (Chinese, Japanese, Korean, Arabic,
        Cyrillic) at any length, full French/Spanish sentences via
        langdetect, or short fragments caught via a diacritic/function-word
        heuristic (with a loanword whitelist so ordinary English sentences
        using words like "café" or "déjà vu" aren't false-flagged).

        Runs on the RAW text, before any cleaning — meant to be checked
        FIRST in the processing loop so foreign-language rows are dropped
        immediately, without wasting time running the full clean_pipeline
        on text that's going to be discarded anyway.
    """
    if not isinstance(text, str):
        return False

    # Non-Latin script — any run, any length, immediate match
    if re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff\u0400-\u04ff]', text):
        return True

    for sent in re.split(r'(?<=[.!?])\s+', text):
        stripped = sent.strip()
        if not stripped:
            continue

        if len(stripped) > 15:
            try:
                if detect(stripped) in ('fr', 'es'):
                    return True
            except LangDetectException:
                pass  # fall through to the heuristic check below

        words = re.findall(r"[a-zà-ÿ']+", stripped.lower())
        
        diacritic_words = [
            w for w in words
            if any(ch in FOREIGN_DIACRITICS for ch in w) and w not in COMMON_LOANWORDS
        ]

        stopword_hits = sum(1 for w in words if w in FRENCH_SPANISH_STOPWORDS)

        if diacritic_words or stopword_hits >= 1:
            return True

    return False


# ==============================================================================
# Placeholder Density Functions
# ==============================================================================

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


def clean_pipeline(text):
    """
    Combined cleaning pipeline for all of the datasets.
    """
    text = clean_url(text)
    text = clean_pseudocode_and_diagrams(text)
    text = clean_code_texts(text)
    text = clean_code_assignments(text)
    text = clean_music_notation(text)
    text = clean_complexity_notation(text)
    text = strip_reference_list(text)
    text = clean_citations(text)
    text = clean_list_numbering(text)
    text = clean_bare_expressions(text)
    text = clean_math_texts(text)
    text = clean_residual_math_noise(text)
    text = merge_continuous_equations(text, tag='[[EQUATION]]')
    text = merge_continuous_equations(text, tag='[[CODE]]')
    text = mop_up_leftover_math_and_code(text)
    text = clean_code_assignments(text)
    text = merge_continuous_equations(text, tag='[[EQUATION]]')
    text = merge_continuous_equations(text, tag='[[CODE]]')
    return text


# ==============================================================================
# Dataset-Specific Cleaning Functions
# ==============================================================================

def extract_claude_prompt_and_response(text):
    """
    Extracts human prompt and claude/gpt response specifically from
    Claude dataset's dictionary-style conversation strings.
    Handles plain text datasets by returning an empty prompt and raw text.
    """
    if not isinstance(text, str):
        return "", str(text)

    if text.strip().startswith('[') and "'from'" in text and "'value'" in text:
        try:
            data = ast.literal_eval(text)
            prompt = ""
            raw_response = ""

            for turn in data:
                if isinstance(turn, dict):
                    role = turn.get('from')
                    val = turn.get('value', '')

                    if role == 'human' and not prompt:
                        prompt = val
                    elif role in ('gpt', 'assistant'):
                        raw_response += val + " "

            return prompt.strip(), raw_response.strip()

        except Exception:
            prompt_match = re.search(r"\{'from':\s*'human',\s*'value':\s*\"\"?(.*?)\"\"?\}", text, flags=re.DOTALL)
            resp_match = re.search(r"\{'from':\s*'(?:gpt|assistant)',\s*'value':\s*\"\"?(.*?)\"\"?\}", text, flags=re.DOTALL)
            prompt = prompt_match.group(1) if prompt_match else ""
            raw_response = resp_match.group(1) if resp_match else text

            return prompt.strip(), raw_response.strip()

    return "", text.strip()


def clean_claude_dataset(claude_csv_path, processed_dir, sample_size=None, density_threshold=0.4, drop_foreign_rows=True):
    """
    Cleans the Claude AI dataset, filters out non-academic creative prompts,
    extracts prompt and cleaned response, filters out placeholder-dense rows
    and rows containing foreign-language content, counts tag insertions,
    displays summary & sample tables, and saves output to processed_dir.

    Args:
        claude_csv_path: Path to the raw Claude CSV file
        processed_dir: Directory path where cleaned CSV will be saved
        sample_size: Number of rows to process (None for all rows)
        density_threshold: Maximum placeholder density ratio (default 0.4)
        drop_foreign_rows: Whether to drop rows with foreign language content

    Returns:
        DataFrame with 'prompt' and 'cleaned_text' columns
    """
    if not claude_csv_path.exists():
        print(f"File not found at: {claude_csv_path}")
        return None

    foreign_skip_counter["too_short"] = 0

    print(f"Loading {'first ' + str(sample_size) if sample_size else 'all'} rows from {claude_csv_path.name}...")
    df_raw = pd.read_csv(claude_csv_path, nrows=sample_size)
    prompts = []
    cleaned_responses = []
    dropped_creative = 0
    dropped_density = 0
    dropped_locally_dense = 0
    dropped_foreign = 0

    print("Cleaning & filtering Claude dataset...")
    for raw_text in tqdm(df_raw['conversations'], desc="Processing Rows"):
        prompt, raw_response = extract_claude_prompt_and_response(str(raw_text))

        if not is_academic_content(prompt, raw_response):
            dropped_creative += 1
            continue

        if drop_foreign_rows and contains_foreign_language(raw_response):
            dropped_foreign += 1
            continue

        cleaned_resp = clean_pipeline(raw_response)

        density = placeholder_density(cleaned_resp)
        if density >= density_threshold:
            dropped_density += 1
            continue

        if placeholder_density_windowed(cleaned_resp):
            dropped_locally_dense += 1
            continue

        prompts.append(prompt)
        cleaned_responses.append(cleaned_resp)

    df_processed = pd.DataFrame({
        'prompt': prompts,
        'cleaned_text': cleaned_responses
    })

    summary_data = {
        "Metric": [
            "Total Rows Loaded",
            "Dropped (Non-Academic/Creative)",
            "Dropped (Foreign-Language Content)",
            "Dropped (Too Placeholder-Dense)",
            "Dropped (Locally Dense Cluster)",
            "Total Academic Rows Kept",
            "[[EQUATION]] Tags Inserted",
            "[[CODE]] Tags Inserted",
            "[[CITATION]] Tags Inserted",
            "[[COMPLEXITY]] Tags Inserted",
            "[[URL]] Tags Inserted",
            "[[MUSIC]] Tags Inserted",
            "Sentences Skipped (Too Short to Detect Language)"
        ],
        "Count": [
            len(df_raw),
            dropped_creative,
            dropped_foreign,
            dropped_density,
            dropped_locally_dense,
            len(df_processed),
            df_processed['cleaned_text'].str.count(r'\[\[EQUATION\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[CODE\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[CITATION\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[COMPLEXITY\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[URL\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[MUSIC\]\]').sum(),
            foreign_skip_counter["too_short"]
        ]
    }
    df_summary = pd.DataFrame(summary_data)

    print("\n--- CLEANING SUMMARY ---")
    ipd.display(df_summary)

    filename = f"claude_dataset_cleaned_{sample_size}.csv" if sample_size else "claude_dataset_cleaned.csv"
    output_path = Path(processed_dir) / filename
    df_processed.to_csv(output_path, index=False)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 20 ROWS) ---")
    ipd.display(df_processed.head(20))

    return df_processed


MGTBENCH_PLACEHOLDER_PATTERN = (
    r'\[\[(?:EQUATION|CODE|CITATION|COMPLEXITY|URL|FOREIGN|MUSIC)\]\]'
)


def flatten_mgtbench_text(text):
    """Flatten escaped and literal newlines/tabs before the shared pipeline."""
    if not isinstance(text, str):
        return text
    text = text.replace('\r', ' ')
    text = text.replace('\n', ' ')
    text = text.replace('\\n', ' ')
    text = text.replace('\\t', ' ')
    return text


def format_mgtbench_equation_tags(text):
    """MGTBench processed output uses single-bracket [EQUATION] tags."""
    if not isinstance(text, str):
        return text
    text = re.sub(r'\[\[EQUATION\]\]', '[EQUATION]', text)
    text = re.sub(r'(?:\s*\[EQUATION\]\s*){2,}', ' [EQUATION] ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_mgtbench_pipeline(text):
    """
    MGTBench cleaning: flatten newlines, run the shared clean_pipeline, then
    format equation tags as [EQUATION] for model input.
    """
    text = flatten_mgtbench_text(text)
    text = clean_pipeline(text)
    text = format_mgtbench_equation_tags(text)
    return text


def _is_mgtbench_placeholder_only(text):
    if not isinstance(text, str) or not text.strip():
        return True
    if re.fullmatch(r'(?:\s*\[EQUATION\]\s*)+', text):
        return True
    return bool(re.fullmatch(rf'(?:{MGTBENCH_PLACEHOLDER_PATTERN}\s*)+', text))


def clean_mgtbench_ai_dataset(mgtbench_csv_path, processed_dir, sample_size=None):
    """
    Cleans the MGTBench AI CSV (id, text, file), drops empty or placeholder-only
    rows, saves to processed_dir, and returns the cleaned DataFrame.
    """
    mgtbench_csv_path = Path(mgtbench_csv_path)
    if not mgtbench_csv_path.exists():
        print(f"File not found at: {mgtbench_csv_path}")
        return None

    print(
        f"Loading {'first ' + str(sample_size) if sample_size else 'all'} rows "
        f"from {mgtbench_csv_path.name}..."
    )
    df = pd.read_csv(mgtbench_csv_path, nrows=sample_size)
    original_rows = len(df)

    df = df.dropna(subset=['text']).copy()
    df['text'] = df['text'].astype(str).str.strip()
    df = df[df['text'] != '']

    print("Cleaning MGTBench AI dataset...")
    cleaned_texts = []
    for text in tqdm(df['text'], total=len(df), desc="Processing Rows", unit="row"):
        cleaned_texts.append(clean_mgtbench_pipeline(text))
    df['text'] = cleaned_texts
    df['text'] = df['text'].str.strip()
    df = df[df['text'] != '']
    df = df[~df['text'].map(_is_mgtbench_placeholder_only)]
    df = df.reset_index(drop=True)

    rows_removed = original_rows - len(df)
    summary_data = {
        'Metric': [
            'Total Rows Loaded',
            'Rows Removed',
            'Cleaned Rows Kept',
            '[EQUATION] Tags Inserted',
            '[[CODE]] Tags Inserted',
            '[[CITATION]] Tags Inserted',
            '[[COMPLEXITY]] Tags Inserted',
            '[[URL]] Tags Inserted',
            'Exact Duplicate Rows',
            'Unique Source Files',
        ],
        'Count': [
            original_rows,
            rows_removed,
            len(df),
            df['text'].str.count(r'\[EQUATION\]').sum(),
            df['text'].str.count(r'\[\[CODE\]\]').sum(),
            df['text'].str.count(r'\[\[CITATION\]\]').sum(),
            df['text'].str.count(r'\[\[COMPLEXITY\]\]').sum(),
            df['text'].str.count(r'\[\[URL\]\]').sum(),
            df.duplicated(subset=['text']).sum(),
            df['file'].nunique() if 'file' in df.columns else None,
        ],
    }

    print("\n--- MGTBENCH AI CLEANING SUMMARY ---")
    ipd.display(pd.DataFrame(summary_data))

    filename = (
        f"mgtbench_ai_dataset_cleaned_{sample_size}.csv"
        if sample_size else "mgtbench_ai_dataset_cleaned.csv"
    )
    output_path = Path(processed_dir) / filename
    df.to_csv(output_path, index=False)
    print(f"\nSuccessfully saved cleaned dataset ({len(df)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 10 ROWS) ---")
    ipd.display(df.head(10))

    return df