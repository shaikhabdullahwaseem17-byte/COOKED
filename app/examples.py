import json
import re
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "style_examples.jsonl"


@lru_cache(maxsize=1)
def load_examples() -> tuple[dict, ...]:
    """Load only well-formed, locally curated examples."""
    records = []
    try:
        lines = DATA_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return tuple()

    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and all(
            isinstance(item.get(key), str) and item[key].strip()
            for key in ("input", "output", "language", "style")
        ):
            records.append(item)
    return tuple(records)


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)
        if len(token) > 2
    }


def select_examples(
    context: str,
    language: str,
    style: str,
    limit: int = 2,
) -> list[dict]:
    """Choose language/style-matched examples with the closest lexical context."""
    if limit <= 0:
        return []

    all_examples = list(load_examples())
    exact = [
        item for item in all_examples
        if item.get("language") == language and item.get("style") == style
    ]
    same_language = [
        item for item in all_examples
        if item.get("language") == language
    ]
    pool = exact if exact else same_language
    if not pool:
        return []

    context_tokens = _tokens(context)

    def relevance(item: dict) -> float:
        example_tokens = _tokens(item["input"])
        if not context_tokens or not example_tokens:
            return 0.0
        return len(context_tokens & example_tokens) / len(context_tokens | example_tokens)

    ranked = sorted(pool, key=relevance, reverse=True)
    return ranked[:limit]
