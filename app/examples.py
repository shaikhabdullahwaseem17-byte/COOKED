import json
import re
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "style_examples.jsonl"

# Common words add little evidence that two situations are actually related.
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "then", "than",
    "you", "your", "his", "her", "she", "him", "he", "they", "them",
    "their", "was", "were", "are", "is", "has", "had", "have", "does",
    "did", "but", "not", "just", "while", "when", "what", "who", "how",
    "into", "onto", "about", "after", "before", "because", "still",
    "posted", "post", "posts",
}


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
        if len(token) > 2 and token not in STOP_WORDS
    }


def select_examples(
    context: str,
    style: str,
    limit: int = 2,
) -> list[dict]:
    """Choose examples only when they share meaningful situation-specific terms."""
    if limit <= 0:
        return []

    all_examples = list(load_examples())
    exact = [
        item for item in all_examples
        if item.get("language", "en") == "en" and item.get("style") == style
    ]
    # Never teach one style using an example from a different style.
    pool = exact
    if not pool:
        return []

    context_tokens = _tokens(context)

    def relevance(item: dict) -> float:
        example_tokens = _tokens(item["input"])
        if not context_tokens or not example_tokens:
            return 0.0
        # One shared generic word (for example, "posted") is not enough to
        # establish that an example is relevant. It can otherwise inject an
        # unrelated premise into the model's context and cause premise drift.
        overlap = len(context_tokens & example_tokens)
        if overlap < 2:
            return 0.0
        return overlap / len(context_tokens | example_tokens)

    scored = [(relevance(item), item) for item in pool]
    ranked = [item for score, item in sorted(scored, key=lambda pair: pair[0], reverse=True)
              if score >= 0.12]
    return ranked[:limit]
