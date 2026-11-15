"""Lightweight output-script checks for COOKED's supported languages.

These checks catch obvious script mismatches; they do not certify grammar,
fluency, idiom, or whether a joke is funny.
"""
from __future__ import annotations

import unicodedata


def _letters(text: str) -> list[str]:
    return [
        char for char in text
        if unicodedata.category(char).startswith("L")
    ]


def is_valid_output(text: str, language: str) -> bool:
    """Reject outputs dominated by a writing system other than the requested one."""
    letters = _letters(text)
    if not letters:
        return False

    if language == "ur-rom":
        # Roman Urdu is intentionally Latin-script; linguistic fluency needs review.
        return sum("LATIN" in unicodedata.name(c, "") for c in letters) / len(letters) >= 0.8

    if language == "ur":
        return sum("ARABIC" in unicodedata.name(c, "") for c in letters) / len(letters) >= 0.65

    if language == "hi":
        return sum("DEVANAGARI" in unicodedata.name(c, "") for c in letters) / len(letters) >= 0.65

    if language == "en":
        return sum("LATIN" in unicodedata.name(c, "") for c in letters) / len(letters) >= 0.8

    return False
