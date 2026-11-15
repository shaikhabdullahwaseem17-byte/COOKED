"""English output checks for COOKED.

These checks reject obvious non-English/script-mismatched generations. They do
not certify grammar, fluency, originality, or whether a joke is funny.
"""
from __future__ import annotations

import unicodedata


def is_valid_output(text: str, language: str = "en") -> bool:
    """Accept English-language Latin-script output and reject other scripts."""
    if language != "en":
        return False
    letters = [
        char for char in text
        if unicodedata.category(char).startswith("L")
    ]
    if not letters:
        return False
    latin = sum("LATIN" in unicodedata.name(char, "") for char in letters)
    return latin / len(letters) >= 0.9
