import re

PRIVATE_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\b(?:\+?\d[\d\s().-]{8,}\d)\b"),
)

BLOCKED_REQUESTS = (
    "write a racist roast",
    "roast them for being disabled",
    "make fun of their disability",
    "humiliate this person",
    "make everyone bully",
    "dox this person",
)

def validate_input(text: str) -> None:
    if any(pattern.search(text) for pattern in PRIVATE_PATTERNS):
        raise ValueError("Remove phone numbers or email addresses before using COOKED.")
    lowered = text.casefold()
    if any(phrase in lowered for phrase in BLOCKED_REQUESTS):
        raise ValueError("COOKED is for playful banter, not targeted harassment.")
