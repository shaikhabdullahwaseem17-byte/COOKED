"""English output checks for COOKED.

These checks reject obvious non-Latin-script generations. They do not
certify grammar, fluency, originality, or whether a joke is funny.
"""
from __future__ import annotations

import unicodedata


def is_valid_output(text: str) -> bool:
    """Accept Latin-script text only; this is not an English fluency test."""
    letters = [
        char for char in text
        if unicodedata.category(char).startswith("L")
    ]
    if not letters:
        return False
    latin = sum("LATIN" in unicodedata.name(char, "") for char in letters)
    return latin == len(letters)
