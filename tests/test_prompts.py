import asyncio

from app.prompts import ANGLES, build_prompt
from app.schemas import RoastRequest
from app.providers import _quality_score


def test_prompt_uses_input_style_and_english():
    prompt = build_prompt("I am always right.", "dry", 2)
    assert "I am always right." in prompt
    assert "understated deadpan" in prompt
    assert "natural contemporary English" in prompt
    assert "5–18 words" in prompt


def test_prompt_has_distinct_angles():
    assert len(ANGLES) == 3
    assert len(set(ANGLES)) == 3


def test_desi_style_is_south_asian_humor_written_in_english():
    prompt = build_prompt("He blames the Wi-Fi for every missed deadline.", "desi", 3)
    assert "South Asian internet humor" in prompt
    assert "natural English" in prompt


def test_request_defaults():
    request = RoastRequest(text="This is enough context.")
    assert request.style == "instagram"
    assert request.intensity == 3
    assert not hasattr(request, "language")


def test_ranker_penalizes_cliche():
    stale = "Even Google cannot find your personality."
    fresh = "Your confidence arrived early; the evidence missed the train."
    assert _quality_score(fresh, "He is always right") > _quality_score(stale, "He is always right")


def test_ranker_rewards_contextual_detail():
    contextual = "The 40-slide deck had confidence; the evidence missed every meeting."
    generic = "Your personality is a loading screen with no progress."
    context = "He made a 40-slide presentation about why he is always right."
    assert _quality_score(contextual, context) > _quality_score(generic, context)


def test_ranker_penalizes_model_preamble():
    assert _quality_score("Sure, here is a hilarious roast for you.", "late reply") < 0


def test_ranker_uses_english_tokens():
    assert isinstance(_quality_score("The evidence took the day off.", "He is always right."), float)


def test_generate_tolerates_partial_provider_failure(monkeypatch):
    import app.providers as providers

    async def fake_complete(prompt, temperature):
        if temperature == 0.98:
            raise RuntimeError("simulated provider hiccup")
        if temperature == 0.88:
            return "The 40-slide deck had confidence; the evidence missed every meeting."
        return "His presentation had more slides than supporting facts."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate("prompt", "He made a 40-slide presentation"))
    assert result in {
        "The 40-slide deck had confidence; the evidence missed every meeting.",
        "His presentation had more slides than supporting facts.",
    }


def test_prompt_includes_original_style_references():
    prompt = build_prompt("He announced his fifth social media break this month.", "instagram", 3)
    assert "STYLE REFERENCES" in prompt
    assert "learn the technique, never copy their wording" in prompt


def test_example_retrieval_respects_style():
    from app.examples import select_examples

    examples = select_examples(
        "He says he is two minutes away while he is still deciding what to wear.",
        "desi",
        limit=2,
    )
    assert examples
    assert all(item["language"] == "en" for item in examples)
    assert all(item["style"] == "desi" for item in examples)


def test_example_retrieval_obeys_limit():
    from app.examples import select_examples
    assert select_examples("Anything", "instagram", limit=0) == []


def test_editor_selects_only_a_generated_candidate(monkeypatch):
    import app.providers as providers

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            return "2"
        if temperature == 0.88:
            return "Candidate one is clever but not quite connected."
        if temperature == 0.98:
            return "The 40-slide deck had confidence; the evidence missed every meeting."
        return "Candidate three is a generic joke about confidence."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate("prompt", "He made a 40-slide presentation"))
    assert result == "The 40-slide deck had confidence; the evidence missed every meeting."


def test_editor_invalid_response_uses_heuristic_fallback(monkeypatch):
    import app.providers as providers

    async def fake_complete(prompt, temperature):
        if temperature == 0.88:
            return "The 40-slide deck had confidence; the evidence missed every meeting."
        if temperature == 0.98:
            return "Even Google cannot find your personality."
        if temperature == 1.05:
            return "His presentation had more slides than supporting facts."
        return "Candidate number two is best."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate("prompt", "40-slide presentation"))
    assert result == "The 40-slide deck had confidence; the evidence missed every meeting."


def test_example_retrieval_never_borrows_a_different_style():
    from app.examples import select_examples
    examples = select_examples("A friend has a huge ego.", "absurd")
    assert all(item["style"] == "absurd" for item in examples)


def test_editor_receives_style(monkeypatch):
    import app.providers as providers
    seen = []

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            seen.append(prompt)
            return "1"
        return "A clever reply that fits this particular situation."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate("prompt", "context", style="desi"))
    assert result == "A clever reply that fits this particular situation."
    assert "requested humor style is desi" in seen[0]


def test_provider_rejects_non_text_model_output(monkeypatch):
    import app.providers as providers

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"message": {"content": {"unexpected": "object"}}}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, *args, **kwargs): return FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    try:
        asyncio.run(providers._complete("prompt", 0.5))
    except providers.ProviderError as exc:
        assert "unexpected response" in str(exc)
    else:
        raise AssertionError("Non-text provider output must be rejected.")


def test_instagram_prompt_targets_native_comment_humor():
    prompt = build_prompt(
        "He posted a 12-minute apology video for being four minutes late.",
        "instagram",
        3,
    )
    assert "top-tier comment under a viral post" in prompt
    assert "screenshot" in prompt
    assert "exact situation" in prompt
    assert "forced slang" in prompt


def test_instagram_editor_prioritizes_specific_punchlines(monkeypatch):
    import app.providers as providers
    seen = []

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            seen.append(prompt)
            return "1"
        return "The apology got a director's cut. The lateness got four minutes."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate(
        "prompt",
        "He posted a 12-minute apology video for being four minutes late.",
        style="instagram",
    ))
    assert result == "The apology got a director's cut. The lateness got four minutes."
    assert "screenshot-worthiness" in seen[0]
    assert "internet-native voice" in seen[0]



def test_prompt_rejects_unrelated_joke_details():
    prompt = build_prompt(
        "He replied 'interesting' and immediately changed the subject.",
        "instagram",
        3,
    )
    assert "Do not invent a new event" in prompt
    assert "comparison must clearly map" in prompt


def test_instagram_editor_prioritizes_grounding(monkeypatch):
    import app.providers as providers
    seen = []

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            seen.append(prompt)
            return "1"
        return "That 'interesting' was a polite exit with the door already closed."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate(
        "prompt",
        "He replied 'interesting' and immediately changed the subject.",
        style="instagram",
    ))
    assert result == "That 'interesting' was a polite exit with the door already closed."
    assert "1. Grounding:" in seen[0]
    assert "random comparisons" in seen[0]
    assert "A simple, exact observation" in seen[0]



def test_example_retrieval_rejects_weak_generic_overlap():
    from app.examples import select_examples

    examples = select_examples(
        "She posted 'no context' and then spent 40 replies explaining the context.",
        "instagram",
        limit=2,
    )
    assert not any("online shopping" in item["input"].casefold() for item in examples)


def test_example_retrieval_requires_meaningful_overlap():
    from app.examples import select_examples

    assert select_examples(
        "A completely unrelated situation with no shared details.",
        "instagram",
        limit=2,
    ) == []



def test_prompt_excludes_diagnosis_based_insults():
    prompt = build_prompt("He rewrote a caption nineteen times.", "instagram", 3)
    assert "medical or mental-health conditions" in prompt
    assert "Never use a diagnosis as an insult" in prompt
