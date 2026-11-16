import re

PRIVATE_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\b(?:\+?\d[\d\s().-]{8,}\d)\b"),
)

# Only reject when an abuse request is explicitly aimed at a sensitive trait,
# appearance, health condition, trauma, or another personal vulnerability.
ABUSE_VERBS = r"(?:roast|mock|make fun of|insult|humiliate|bully|shame|drag)"
TARGET_TRAITS = (
    r"(?:race|ethnicity|religion|faith|muslim|christian|jewish|hindu|sikh|buddhist|atheist|nationality|sexual orientation|"
    r"gender identity|disability|disabled|autistic|autism|adhd|hijab|kippah|turban|"
    r"down syndrome|blind|deaf|wheelchair user|depression|anxiety|"
    r"mental health|trauma|appearance|looks|body|weight|height|face|"
    r"skin|hair|acne|ugly|fat|skinny)"
)
TARGETED_ABUSE_PATTERNS = (
    re.compile(
        rf"\b{ABUSE_VERBS}\b.{{0,80}}\b(?:for being|because\s+"
        rf"(?:he|she|they|someone)\s+(?:is|are|has|have)|for\s+"
        rf"(?:their|his|her)|(?:their|his|her|a|an|the))\s+"
        rf"{TARGET_TRAITS}\b",
        re.IGNORECASE,
    ),
)

BLOCKED_REQUESTS = (
    "write a racist roast",
    "humiliate this person",
    "make everyone bully",
    "encourage people to harass",
    "dox this person",
    "share their private information",
)


def validate_input(text: str) -> None:
    """Reject exposed contact details and explicit targeted-harassment requests."""
    if any(pattern.search(text) for pattern in PRIVATE_PATTERNS):
        raise ValueError("Remove phone numbers or email addresses before using COOKED.")

    lowered = text.casefold()
    if any(phrase in lowered for phrase in BLOCKED_REQUESTS):
        raise ValueError("COOKED is for playful banter, not targeted harassment.")

    if any(pattern.search(text) for pattern in TARGETED_ABUSE_PATTERNS):
        raise ValueError(
            "COOKED targets situations and choices, not identity, appearance, "
            "health conditions, trauma, or personal vulnerabilities."
        )



def is_safe_output(text: str) -> bool:
    """Apply the same privacy and targeted-abuse checks to generated comments.

    This is a narrow deterministic guard, not a complete moderation system.
    """
    try:
        validate_input(text)
    except ValueError:
        return False
    return True
