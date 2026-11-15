LANGUAGE = {
    "en": "natural contemporary English",
    "ur": "natural Urdu written in Urdu script",
    "ur-rom": "natural Pakistani Roman Urdu as people actually type online",
    "hi": "natural contemporary Hindi",
}

STYLE = {
    "instagram": "Instagram comment-section wit: compact, specific, surprising, casually sharp.",
    "dry": "Dry, understated deadpan. Let the observation do the work.",
    "desi": "Culturally aware South Asian internet humor. Natural idiom, never fake accent or forced slang.",
    "absurd": "Unexpected, surreal, clever absurdity. Keep the connection to the input clear.",
}

ANGLES = (
    "Use a sharp observation and a quick reversal.",
    "Use an unexpected but relevant comparison; avoid a stock meme template.",
    "Use dry understatement or a compact double meaning.",
)

def build_prompt(text: str, language: str, style: str, intensity: int) -> str:
    return f"""You write genuinely funny, short internet comments. Produce ONE excellent playful comeback, not a list.

INPUT:
{text}

OUTPUT LANGUAGE: {LANGUAGE[language]}
HUMOR STYLE: {STYLE[style]}
INTENSITY: {intensity}/5
QUALITY BAR:
- Find the most roastable specific detail or contradiction in the input.
- Make one clean comedic turn. Specificity beats generic aggression.
- Sound like a naturally funny person in a comment section, not a chatbot performing "savage".
- Aim for 5–18 words. Never pad the line.
- No explanation, preamble, labels, multiple options, hashtags or emoji spam.
- Avoid stale templates, generic insults and forced slang.
- Write naturally in the requested language; do not translate English jokes word-for-word.
- If context is thin, make a light observation about the wording rather than inventing personal facts.
- Keep it playful. Do not target protected traits, appearance, disability, trauma, private information or vulnerabilities.
- No threats, sexual content, slurs or encouragement of dogpiling.

Return only the comeback."""
