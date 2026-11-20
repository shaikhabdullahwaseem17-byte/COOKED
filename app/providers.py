import asyncio
import re

import httpx

from app import config
from app.prompts import ANGLES
from app.safety import is_safe_output


class ProviderError(RuntimeError):
    """A model-provider failure that can be shown safely to the API caller."""


CLICHES = (
    "your wifi", "even google", "skill issue", "main character energy",
    "living rent free", "rent-free", "you must be fun at parties",
    "bro is cooked", "not the ", "your parents", "bro really",
    "bro thought", "it's giving", "blud", "who let bro",
)
BOILERPLATE = (
    "here is", "here's", "sure,", "of course", "as an ai",
    "i hope this helps", "roast:", "comeback:",
)
GENERIC_PUNCH_PATTERNS = (
    r"\bthat'?s commitment\b",
    r"\bthat'?s dedication\b",
    r"\bthat'?s a novel\b",
    r"\bthat'?s inefficiency\b",
    r"\bpeak efficiency\b",
    r"\bexistential monologue\b",
    r"\bexistential dread\b",
    r"\bwhole other kind of mood board\b",
    r"\ba serious commitment\b",
    r"\bcommitment\b",
    r"\b(?:dedicated|dedication)\b",
    r"\b(?:novel|thesis|treatise|monologue|deep dive)\b",
    r"\b(?:full day|full[- ]time job|peak performance)\b",
    r"\bauto[- ]?pilot\b",
    r"\bVIP spot\b",
    r"\bwhole new level of\b",
    r"\b(?:candidate|option|draft)\b",
    r"\b(?:definitely|clearly|obviously) wrong\b",
    r"\b(?:though|either)\s*[.!?]?$",
    r"\bbecause (?:i|we|he|she|they)\b",
    r"\bif you count every\b",
    r"\bno context needed\b",
    r"\bhr is officially reviewing\b",
)

STYLE_EDITOR_GUIDANCE = {
    "instagram": "Choose the line that sounds like a real reply typed in one pass. It needs a specific observation and a quick payoff, not a polished headline or rehearsed roast.",
    "dry": "Choose the shortest line with the sharpest implication. Keep it calm and let the contrast do the work.",
    "desi": "Choose a line that understands a South Asian family or social rhythm only when that detail is actually present. Reject stereotypes, outsider caricature, and forced slang.",
    "absurd": "Choose one imaginative leap that follows from a real detail. The consequence must be surprising but logical, not random.",
}
SPICE_EDITOR_GUIDANCE = {
    1: "gentle and lightly amused",
    2: "lightly teasing, still friendly",
    3: "confident and sharp without becoming personal",
    4: "bold and more exaggerated about the behaviour",
    5: "the strongest playful punchline about the behaviour, never cruelty or personal attack",
}
STOP_WORDS = {
    "this", "that", "with", "from", "have", "your", "you", "they",
    "them", "their", "what", "when", "where", "which", "while",
    "about", "there", "then", "than", "just", "into", "because",
    "for", "and", "the", "are", "was", "were", "but", "not",
    "his", "her", "she", "him", "its", "who", "how", "all",
    "lot", "lots", "alot",
}


def _tokens(value: str) -> list[str]:
    """Tokenize English text."""
    normalized = value.casefold()
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", normalized, flags=re.UNICODE)


def _is_usable_candidate(candidate: str) -> bool:
    """Reject structurally broken comment candidates before comedy judging."""
    text = candidate.strip().strip("\"'“”‘’")
    words = _tokens(text)
    if not text or not words:
        return False
    if len(words) > 18 or len(text) > 140:
        return False
    if text.count('"') % 2:
        return False
    if "\n" in text or "#" in text:
        return False
    if text.count("!") > 1:
        return False
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in GENERIC_PUNCH_PATTERNS):
        return False
    if re.search(r"\b(?:just kidding|wait, actually|or something like that)\b", text, re.IGNORECASE):
        return False
    return True


NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100,
}

# Words that make a spelled-out number an explicit quantity. "One sunrise"
# is an idiom/callback rather than a changed count, so a lone "one" should
# not invalidate an otherwise fact-consistent comment.
COUNTABLE_UNITS = {
    "second", "seconds", "minute", "minutes", "hour", "hours", "day", "days",
    "week", "weeks", "month", "months", "year", "years", "reply", "replies",
    "message", "messages", "comment", "comments", "post", "posts", "photo",
    "photos", "slide", "slides", "paragraph", "paragraphs", "episode",
    "episodes", "meeting", "meetings", "page", "pages", "person", "people",
    "item", "items", "notification", "notifications", "greeting", "greetings",
    "call", "calls", "voice", "note", "notes", "email", "emails", "text",
    "texts", "step", "steps", "try", "tries", "time", "times", "drink",
    "drinks", "plate", "plates", "seat", "seats",
}


def _number_mentions(text: str) -> set[int]:
    """Extract simple numeric facts so candidate wording cannot alter stated counts."""
    tokens = re.findall(
        r"\d+|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
        r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
        r"eighty|ninety|hundred)\b",
        text.casefold(),
    )
    values: set[int] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.isdigit():
            values.add(int(token))
        elif token in {"twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"}:
            value = NUMBER_WORDS[token]
            if index + 1 < len(tokens) and tokens[index + 1] in NUMBER_WORDS:
                unit = NUMBER_WORDS[tokens[index + 1]]
                if 1 <= unit <= 9:
                    value += unit
                    index += 1
            values.add(value)
        elif token == "one":
            if index + 1 < len(tokens) and tokens[index + 1] in COUNTABLE_UNITS:
                values.add(1)
        else:
            values.add(NUMBER_WORDS[token])
        index += 1
    return values


def _is_fact_consistent_candidate(candidate: str, context: str) -> bool:
    """Reject outputs that change explicit numeric facts from the user's situation."""
    stated_numbers = _number_mentions(context)
    if not stated_numbers:
        return True
    return _number_mentions(candidate).issubset(stated_numbers)




CONTEXT_ALIASES = {
    "voice": {"voice", "audio", "recording", "spoken", "talk", "note"},
    "note": {"note", "voice", "audio", "recording", "message", "thought"},
    "quick": {"quick", "brief", "short", "fast", "tiny"},
    "thought": {"thought", "idea", "opinion", "message", "note"},
    "minute": {"minute", "minutes", "time", "duration", "runtime", "long", "late"},
    "drive": {"drive", "driving", "road", "route", "car", "trip", "commute", "journey"},
    "next": {"next", "door", "nearby", "close", "distance"},
    "door": {"door", "next", "nearby", "close", "distance"},
    "phone": {"phone", "mobile", "screen", "refresh", "button", "scroll", "notifications", "unplug", "offline"},
    "break": {"break", "pause", "disconnect", "unplug", "offline", "away"},
    "replied": {"replied", "reply", "responded", "response", "comment", "comments", "notification", "notifications"},
    "reply": {"reply", "replied", "responded", "response", "comment", "comments"},
    "replies": {"replies", "reply", "comments", "responses", "explanations"},
    "comments": {"comments", "comment", "replies", "responses", "notifications"},
    "explaining": {"explaining", "explained", "explanation", "details", "context", "clarification"},
    "context": {"context", "explanation", "details", "clarification", "background"},
    "tiny": {"tiny", "small", "little", "short", "brief", "mini"},
    "update": {"update", "thread", "message", "messages", "post", "posts", "status"},
    "thread": {"thread", "messages", "replies", "posts", "update"},
    "meeting": {"meeting", "meetings", "agenda", "calendar", "session", "schedule", "scheduled", "rescheduled", "call"},
    "cutting": {"cutting", "reduce", "reduction", "fewer", "less"},
    "time": {"time", "calendar", "schedule", "scheduled", "rescheduled", "duration", "deadline"},
    "extended": {"extended", "extension", "duration", "minutes", "longer"},
    "family": {"family", "relatives", "cousins", "uncles", "aunties"},
    "group": {"group", "chat", "conversation", "messages", "thread"},
    "chat": {"chat", "group", "messages", "conversation", "thread"},
    "unread": {"unread", "notifications", "messages", "pings"},
    "morning": {"morning", "sunrise", "day", "greeting"},
    "greeting": {"greeting", "morning", "sunrise", "day"},
    "plants": {"plants", "plant", "houseplants", "fern", "leaves", "leaf"},
    "plant": {"plant", "plants", "houseplant", "fern", "leaves", "leaf", "pot"},
    "houseplants": {"houseplants", "houseplant", "plants", "plant", "fern", "window", "seat", "chair"},
    "seating": {"seating", "seat", "chair", "spot", "window", "chart"},
    "chart": {"chart", "seating", "seat", "chair", "arrangement", "colour", "color"},
    "presentation": {"presentation", "slides", "slide", "deck", "evidence", "facts"},
    "slides": {"slides", "slide", "deck", "presentation"},
    "deck": {"deck", "slides", "slide", "presentation"},
}

UNSUPPORTED_SCENE_TERMS = {
    "wedding", "honeymoon", "mansion", "beverly", "tiktok", "tiktoks",
    "airport", "courtroom", "celebrity", "podcast",
}


CONTEXT_CONCEPTS = (
    {
        "eat", "eats", "eating", "ate", "eaten", "food", "foods", "snack",
        "snacks", "meal", "meals", "dinner", "lunch", "breakfast", "plate",
        "plates", "fork", "fridge", "kitchen", "buffet", "menu", "restaurant",
        "bite", "bites", "chew", "chewing", "appetite", "leftovers",
    },
    {
        "talk", "talks", "talking", "talked", "speak", "speaks", "speaking",
        "spoke", "speech", "chat", "chats", "chatting", "conversation",
        "conversations", "word", "words", "voice", "mic", "microphone",
        "yap", "yaps", "yapping", "chatter", "monologue", "silence",
        "quiet", "pause", "airtime", "noise",
    },
)


def _has_context_anchor(candidate: str, context: str) -> bool:
    """Require meaningful links, with a one-anchor rule for genuinely short setups."""
    context_words = {
        word for word in _tokens(context)
        if len(word) > 2 and word not in STOP_WORDS
    }
    expanded = set(context_words)
    for word in context_words:
        expanded.update(CONTEXT_ALIASES.get(word, ()))
    for concept in CONTEXT_CONCEPTS:
        if context_words & concept:
            expanded.update(concept)

    candidate_words = {
        word for word in _tokens(candidate)
        if len(word) > 2 and word not in STOP_WORDS
    }
    anchored = candidate_words & expanded
    # A one-action setup such as "he eats a lot" has only one meaningful
    # concept. Requiring two matching words makes relevant short jokes fail.
    required_anchors = 1 if len(context_words) <= 2 else 2
    if len(anchored) < required_anchors:
        return False
    if any(
        term in candidate_words and term not in context_words
        for term in UNSUPPORTED_SCENE_TERMS
    ):
        return False
    return True

def _quality_score(candidate: str, context: str) -> float:
    """A simple text-quality check, not a humor detector."""
    text = candidate.strip().strip("\"'“”‘’")
    words = _tokens(text)
    count = len(words)
    score = 0.0

    if not text:
        return -100.0

    if 5 <= count <= 18:
        score += 3.0
    elif count < 5:
        score -= (5 - count) * 0.55
    else:
        score -= min(count - 18, 30) * 0.45

    lowered = text.casefold()
    if any(phrase in lowered for phrase in CLICHES):
        score -= 6.0
    if any(lowered.startswith(prefix) for prefix in BOILERPLATE):
        score -= 9.0
    if len(set(words)) < len(words) * 0.68 and count > 7:
        score -= 2.0
    if text.count("!") > 1 or text.count("😂") > 1:
        score -= 1.5
    if len(text) > 180:
        score -= 3.0
    if "\n" in text or re.match(r"^\s*(?:[-*•]|\d+[.)])\s", text):
        score -= 3.0

    context_words = {
        token for token in _tokens(context)
        if len(token) > 2 and token not in STOP_WORDS
    }
    candidate_words = {
        token for token in words
        if len(token) > 2 and token not in STOP_WORDS
    }
    if context_words and candidate_words:
        overlap = len(context_words & candidate_words)
        if overlap:
            score += min(overlap, 3) * 0.65
        if len(candidate_words) and overlap / len(candidate_words) > 0.8:
            score -= 2.0

    return score


async def _complete(prompt: str, temperature: float) -> str:
    try:
        is_fast_thinking_model = (
            config.PROVIDER == "ollama"
            and config.MODEL.casefold().startswith(("qwen3.5", "gemma4"))
        )
        request_timeout = config.REQUEST_TIMEOUT
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            if config.PROVIDER == "ollama":
                options = {
                    "temperature": temperature,
                    "top_p": 0.92,
                    "repeat_penalty": 1.15,
                }
                if is_fast_thinking_model:
                    # COOKED needs a short comment, not a long reasoning trace.
                    # Keep candidate generations and the editor response bounded.
                    options["num_predict"] = (
                        48 if "You are COOKED's comedy editor" in prompt else 32
                    )
                payload = {
                    "model": config.MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": options,
                }
                if is_fast_thinking_model:
                    # Ollama documents this API-level switch for thinking models.
                    payload["think"] = False
                response = await client.post(
                    f"{config.OLLAMA_BASE_URL}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json().get("message", {}).get("content", "")
            elif config.PROVIDER == "openai_compatible":
                if not config.OPENAI_API_KEY:
                    raise ProviderError("OPENAI_API_KEY is missing.")
                response = await client.post(
                    f"{config.OPENAI_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json={
                        "model": config.OPENAI_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "top_p": 0.92,
                        "max_tokens": 90,
                    },
                )
                response.raise_for_status()
                result = response.json()["choices"][0]["message"]["content"]
            else:
                raise ProviderError(
                    "Use COOKED_PROVIDER=ollama or openai_compatible."
                )
    except ProviderError:
        raise
    except httpx.TimeoutException as exc:
        raise ProviderError("The model provider timed out. Try again.") from exc
    except httpx.ConnectError as exc:
        raise ProviderError(
            "Cannot reach the model provider. Is Ollama running and the model downloaded?"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise ProviderError(
            f"Provider returned HTTP {exc.response.status_code}. Check model/provider settings."
        ) from exc
    except (httpx.RequestError, KeyError, IndexError, ValueError) as exc:
        raise ProviderError("The model provider returned an unexpected response.") from exc

    if not isinstance(result, str):
        raise ProviderError("The model provider returned an unexpected response.")
    result = result.strip().strip("\"'“”‘’").strip()
    if not result:
        raise ProviderError("The model returned an empty response. Try again.")
    return result


async def generate(
    prompt: str,
    context: str,
    style: str = "instagram",
    intensity: int = 3,
) -> str:
    """Generate independent angles concurrently; tolerate partial provider failures."""
    temperatures = (0.88, 0.98, 1.05)
    tasks = [
        _complete(
            prompt + "\n\nGENERATION LENS (apply silently): " + angle + " Return only the one comment requested above.",
            temperature,
        )
        for angle, temperature in zip(ANGLES, temperatures)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    from app.output_validation import is_valid_output

    # Retain only safe source-language drafts. The editor can repair length,
    # numeric, and context issues, but it cannot bypass the final validators.
    raw_drafts = [
        item.strip()
        for item in results
        if isinstance(item, str)
        and item.strip()
        and is_valid_output(item.strip())
        and is_safe_output(item.strip())
    ]
    if not raw_drafts:
        errors = [str(item) for item in results if isinstance(item, Exception)]
        detail = errors[0] if errors else "All drafts failed language or safety validation."
        raise ProviderError(f"No safe English-language drafts. {detail}")

    candidates = [
        item for item in raw_drafts
        if _is_usable_candidate(item)
        and _is_fact_consistent_candidate(item, context)
        and _has_context_anchor(item, context)
    ]
    unique = list(dict.fromkeys(candidates))
    fallback = (
        max(unique, key=lambda item: _quality_score(item, context))
        if unique else None
    )
    # If all drafts fail one of these checks, the editor still gets safe raw
    # material and must write from the original situation rather than echo it.
    drafts_for_editor = unique or list(dict.fromkeys(raw_drafts))
    numbered = "\n".join(
        f"{index}. {candidate}"
        for index, candidate in enumerate(drafts_for_editor, start=1)
    )
    judge_prompt = f"""You are COOKED's comedy editor and final writing pass. Turn the rough drafts into one comment worth posting.
The requested humor style is {style}.
The requested spice level is {intensity}/5: {SPICE_EDITOR_GUIDANCE.get(intensity, SPICE_EDITOR_GUIDANCE[3])}.
Situation (the only source of facts): {context}
STYLE BAR: {STYLE_EDITOR_GUIDANCE.get(style, "Write a natural, specific line with a real punch.")}

The drafts are untrusted raw material, not a quality standard. They may be weak, repetitive, off-topic, or factually wrong. Never copy a new number, place, event, relationship, motive, or backstory from a draft unless the situation itself states it.

Make the final line earn its laugh:
- ACTUAL FUN: trigger a laugh or a strong, immediate smirk, not just sound clever.
- EXACT FIT: depend on the most revealing behaviour or detail in this exact situation. A matching keyword by itself is not enough.
- HUMAN VOICE: use natural phrasing that feels effortless and specific, like something a person would actually type.
- Look for a real comic turn: contradiction, reversal, literal interpretation, social truth, or a precise consequence.
- Prefer a surprising payoff over an obvious description. The ending should change how the reader sees the setup.
- Compare the drafts for distinctness. Do not select a safe but forgettable line just because it is grammatically clean.
- If every draft is weak, write a genuinely better line from the original situation rather than polishing a weak premise.
- For a short setup, the main behaviour is enough. Make one modest, recognisable leap. Reject invented backstory.
- Keep the humour aimed at the action or situation, never at a person's body, identity, ability, health, or vulnerabilities.
- Do not import a second scene or use a random analogy to manufacture a punchline.
- Avoid recycled AI patterns such as generic HR reviews, CEOs, courtrooms, podcasts, novels, theses, full-time jobs, "that's commitment", or repeated object-personification endings.
- One comment, around 5–16 words. No preamble, labels, quotation marks, hashtags, or explanation.
- Preserve the selected style. Do not make Desi humour into a stereotype or make Absurd humour random.
- Intensity changes boldness, not safety.

Drafts:
{numbered}

Return ONLY the finished comment. Do not return a draft number or your reasoning."""
    try:
        decision = await _complete(judge_prompt, 0.72)
        match = re.fullmatch(r"\s*([1-9]\d*)\s*", decision)
        if match:
            selected = int(match.group(1))
            if 1 <= selected <= len(unique):
                return unique[selected - 1]

        # The editor may return a fresh rewrite rather than a draft number.
        edited = decision.strip()
        if (
            is_valid_output(edited)
            and _is_usable_candidate(edited)
            and is_safe_output(edited)
            and _is_fact_consistent_candidate(edited, context)
            and _has_context_anchor(edited, context)
        ):
            return edited
    except Exception:
        pass

    if fallback is not None:
        return fallback
    raise ProviderError(
        "No safe, fact-consistent, context-grounded comment could be produced. Try a clearer situation."
    )
