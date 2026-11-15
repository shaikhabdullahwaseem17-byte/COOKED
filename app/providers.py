import asyncio
import re
import httpx
from app import config
from app.prompts import ANGLES

class ProviderError(RuntimeError):
    pass

CLICHES = (
    "your wifi has more", "even google", "skill issue", "main character energy",
    "living rent free", "you must be fun at parties", "bro is cooked",
    "not the ", "your parents", "rent-free",
)

def _quality_score(candidate: str, context: str) -> float:
    text = candidate.strip().strip('"\'')
    words = re.findall(r"[\w’'-]+", text.casefold())
    count = len(words)
    score = 0.0
    if 5 <= count <= 18:
        score += 3.0
    elif count < 5:
        score -= (5 - count) * 0.7
    else:
        score -= min(count - 18, 20) * 0.35
    if any(cliche in text.casefold() for cliche in CLICHES):
        score -= 5.0
    if re.match(r"^(sure|here('| i)s|of course|as an ai|roast:)", text.casefold()):
        score -= 8.0
    if len(set(words)) < len(words) * 0.72 and count > 7:
        score -= 2.0
    if text.count("!") > 1 or text.count("😂") > 1:
        score -= 1.5
    context_words = set(re.findall(r"[a-zA-Z]{4,}", context.casefold()))
    candidate_words = set(re.findall(r"[a-zA-Z]{4,}", text.casefold()))
    if context_words and candidate_words.intersection(context_words):
        score += 0.5
    if len(text) > 180:
        score -= 3.0
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
                        "options": {"temperature": temperature, "top_p": 0.92, "repeat_penalty": 1.15},
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
                raise ProviderError("Use COOKED_PROVIDER=ollama or openai_compatible.")
    except ProviderError:
        raise
    except httpx.ConnectError as exc:
        raise ProviderError("Cannot reach the model provider. Is Ollama running and the model downloaded?") from exc
    except httpx.HTTPStatusError as exc:
        raise ProviderError(f"Provider returned HTTP {exc.response.status_code}. Check model/provider settings.") from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise ProviderError("Provider returned an unexpected response.") from exc

    result = (result or "").strip().strip('"\'').strip()
    if not result:
        raise ProviderError("The model returned an empty response. Try again.")
    return result

async def generate(prompt: str, context: str) -> str:
    temperatures = (0.88, 0.98, 1.05)
    tasks = [
        _complete(prompt + "\n\nTry this distinct comedic approach: " + angle, temperature)
        for angle, temperature in zip(ANGLES, temperatures)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    candidates = [item for item in results if isinstance(item, str) and item.strip()]
    if not candidates:
        errors = [str(item) for item in results if isinstance(item, Exception)]
        raise ProviderError(errors[0] if errors else "The model returned no usable candidates.")
    return max(candidates, key=lambda item: _quality_score(item, context))
