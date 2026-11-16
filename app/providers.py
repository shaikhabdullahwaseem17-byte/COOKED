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
    "instagram": "Choose the line that feels most like a real person's quick comment: instantly recognizable, naturally phrased, and finished on its punch. Reject anything that reads like a headline or scripted roast.",
    "dry": "Choose the quietest line with the sharpest implication. It should sound almost matter-of-fact, not like it is announcing a joke.",
    "desi": "Choose a line that understands the specific family or social rhythm in the situation. Reject outsider caricature, generic family jokes, and forced slang.",
    "absurd": "Choose the strangest line that still follows cleanly from one real detail. Reject randomness disguised as creativity.",
}
STOP_WORDS = {
    "this", "that", "with", "from", "have", "your", "you", "they",
    "them", "their", "what", "when", "where", "which", "while",
    "about", "there", "then", "than", "just", "into", "because",
    "for", "and", "the", "are", "was", "were", "but", "not",
    "his", "her", "she", "him", "its", "who", "how", "all",
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
    "wedding", "mansion", "beverly", "tiktok", "tiktoks",
}


def _has_context_anchor(candidate: str, context: str) -> bool:
    """Require a rewrite to retain multiple details tied to the supplied situation."""
    context_words = set(_tokens(context))
    expanded = set(context_words)
    for word in context_words:
        expanded.update(CONTEXT_ALIASES.get(word, ()))
    candidate_words = {
        word for word in _tokens(candidate)
        if len(word) > 2 and word not in STOP_WORDS
    }
    anchored = candidate_words & expanded
    if len(anchored) < 2:
        return False
    if any(
        term in candidate_words and term not in context_words
        for term in UNSUPPORTED_SCENE_TERMS
    ):
        return False
    return True


def _quality_score(candidate: str, context: str) -> float:
    """A deliberately simple anti-slop heuristic, not a humor detector."""
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

    # Keep safe model drafts even when they are too long or factually sloppy.
    # The final writer can repair them against the original situation.
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
    # If every draft failed the length, fact, or context-fit checks, the editor
    # still gets safe raw material and must rewrite from the original situation.
    drafts_for_editor = unique or list(dict.fromkeys(raw_drafts))
    numbered = "\n".join(
        f"{index}. {candidate}" for index, candidate in enumerate(drafts_for_editor, start=1)
    )
    judge_prompt = f"""You are COOKED's comedy editor and final writing pass. Your job is to turn rough drafts into one comment worth posting.
The requested humor style is {style}.
Situation: {context}
STYLE BAR: {STYLE_EDITOR_GUIDANCE.get(style, "Write a natural, specific line with a real punch.")}

The drafts below are untrusted raw material, NOT a quality standard. They may be too long, off-topic, or contain made-up details. The situation above is the only source of truth. Never copy a new number, place, event, relationship, or backstory from a draft unless the situation itself states it.
Judge the rewrite by this rubric:
- ACTUAL FUN: it should trigger a laugh or a strong, immediate smirk, not just sound clever.
- EXACT FIT: the line must depend on this exact situation and its most revealing detail.
- HUMAN VOICE: a strong line feels effortless and specific, like a comment typed in one pass.
- PAYOFF: the ending must change the interpretation, not merely repeat the setup.
Your task:
- Find the one detail in the situation with the strongest comic potential.
- Create a fresh line with a genuinely different and funnier interpretation.
- Make the joke depend on that exact detail, not a generic insult or a summary.
- Prefer a clean reframe, a recognisable social truth, or a precise unexpected consequence.
- Make the last few words do the work. Use conversational English that sounds typed, not performed.
- If the drafts contain a useful idea, sharpen it. Do not preserve bad wording just because it is in a draft.
- Reject invented backstory. Do not add facts, relationships, places, motives, counts, or events that the situation does not supply.
- Do not explain the joke, narrate what happened, or tell the reader that someone is wrong.
- Avoid generic AI scaffolds such as HR reviews, CEOs, courtrooms, podcasts, novels, theses, full-time jobs, and vague "that's commitment" endings.
- Keep it to one comment of 5–16 words, with no preamble, quotation marks, labels, or explanation.
- Respect the safety rules: no attacks on identity, appearance, disability, health, trauma, private information, or personal vulnerabilities.

Drafts:
{numbered}

Return ONLY the finished comment. Do not return a draft number."""
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
