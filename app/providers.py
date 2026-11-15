import asyncio
import re
import unicodedata

import httpx

from app import config
from app.prompts import ANGLES


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
STOP_WORDS = {
    "this", "that", "with", "from", "have", "your", "you", "they",
    "them", "their", "what", "when", "where", "which", "while",
    "about", "there", "then", "than", "just", "into", "because",
    "for", "and", "the", "are", "was", "were", "but", "not",
    "his", "her", "she", "him", "its", "who", "how", "all",
}


def _tokens(value: str) -> list[str]:
    """Unicode-aware tokenization for English, Urdu, Hindi and Roman Urdu."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", normalized, flags=re.UNICODE)


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
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            if config.PROVIDER == "ollama":
                response = await client.post(
                    f"{config.OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": config.MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "top_p": 0.92,
                            "repeat_penalty": 1.15,
                        },
                    },
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
    language: str = "en",
    style: str = "instagram",
) -> str:
    """Generate independent angles concurrently; tolerate partial provider failures."""
    temperatures = (0.88, 0.98, 1.05)
    tasks = [
        _complete(
            prompt + "\n\nTry this distinct comedic approach: " + angle,
            temperature,
        )
        for angle, temperature in zip(ANGLES, temperatures)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    candidates = [
        item.strip()
        for item in results
        if isinstance(item, str) and item.strip()
    ]
    if not candidates:
        errors = [str(item) for item in results if isinstance(item, Exception)]
        raise ProviderError(
            errors[0] if errors else "The model returned no usable candidates."
        )

    unique = list(dict.fromkeys(candidates))
    fallback = max(unique, key=lambda item: _quality_score(item, context))

    # A separate editor pass judges only the generated candidates. It cannot
    # invent a replacement, and a failed/invalid judge safely falls back.
    numbered = "\n".join(
        f"{index}. {candidate}" for index, candidate in enumerate(unique, start=1)
    )
    judge_prompt = f"""You are COOKED's comedy editor. Select the single funniest candidate.
The requested output language is {language}; the requested humor style is {style}.
Judge whether each candidate sounds natural in that language and fits that style.

Judge by these priorities:
1. Specific connection to the supplied situation (not a generic insult).
2. A surprising, clear punchline that sounds natural in the requested language.
3. Originality; reject stale templates, forced slang, and chatbot phrasing.
4. Brevity without sacrificing the joke.

Do not rewrite, explain, or invent a candidate. Choose only from the numbered list.
Situation: {context}

Candidates:
{numbered}

Reply with ONLY the candidate number."""
    try:
        decision = await _complete(judge_prompt, 0.12)
        match = re.fullmatch(r"\s*([1-9]\d*)\s*", decision)
        if match:
            selected = int(match.group(1))
            if 1 <= selected <= len(unique):
                return unique[selected - 1]
    except Exception:
        pass

    return fallback
