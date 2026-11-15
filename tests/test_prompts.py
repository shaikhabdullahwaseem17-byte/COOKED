from app.prompts import ANGLES, build_prompt
from app.schemas import RoastRequest
from app.providers import _quality_score


def test_prompt_uses_input_and_style():
    prompt = build_prompt("I am always right.", "en", "dry", 2)
    assert "I am always right." in prompt
    assert "understated deadpan" in prompt
    assert "5–18 words" in prompt


def test_prompt_has_distinct_angles():
    assert len(ANGLES) == 3
    assert len(set(ANGLES)) == 3


def test_urdu_prompt_requests_natural_urdu():
    prompt = build_prompt("وہ ہر بات پر ماہر بنتا ہے", "ur", "desi", 3)
    assert "natural, conversational Pakistani Urdu" in prompt


def test_roman_urdu_prompt_requests_native_rhythm():
    prompt = build_prompt("Woh har baat pe expert banta hai", "ur-rom", "desi", 3)
    assert "natural Pakistani Roman Urdu" in prompt
    assert "literal translation" in prompt


def test_request_defaults():
    request = RoastRequest(text="This is enough context.")
    assert request.language == "en"
    assert request.style == "instagram"
    assert request.intensity == 3


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


def test_ranker_accepts_unicode_tokens():
    assert isinstance(_quality_score("اعتماد پورا ہے، ثبوت چھٹی پر ہیں۔", "وہ ہر بات پر ماہر بنتا ہے"), float)
    assert isinstance(_quality_score("आत्मविश्वास पूरा है, सबूत छुट्टी पर हैं।", "वह हर बात पर विशेषज्ञ है"), float)


def test_generate_tolerates_partial_provider_failure(monkeypatch):
    import asyncio
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
    prompt = build_prompt(
        "He announced his fifth social media break this month.",
        "en",
        "instagram",
        3,
    )
    assert "STYLE REFERENCES" in prompt
    assert "learn the technique, never copy their wording" in prompt


def test_example_retrieval_respects_language_and_style():
    from app.examples import select_examples

    examples = select_examples(
        "Woh har baat pe expert banta hai.",
        "ur-rom",
        "desi",
        limit=2,
    )
    assert examples
    assert all(item["language"] == "ur-rom" for item in examples)
    assert all(item["style"] == "desi" for item in examples)


def test_example_retrieval_returns_empty_for_unknown_language():
    from app.examples import select_examples

    assert select_examples("A context", "xx", "instagram") == []


def test_example_retrieval_obeys_limit():
    from app.examples import select_examples

    assert len(select_examples("Anything", "en", "instagram", limit=0)) == 0


def test_editor_selects_only_a_generated_candidate(monkeypatch):
    import asyncio
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
    result = asyncio.run(
        providers.generate("prompt", "He made a 40-slide presentation")
    )
    assert result == "The 40-slide deck had confidence; the evidence missed every meeting."


def test_editor_invalid_response_uses_heuristic_fallback(monkeypatch):
    import asyncio
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

    examples = select_examples("A friend has a huge ego.", "en", "absurd")
    assert examples == []


def test_editor_receives_requested_language_and_style(monkeypatch):
    import asyncio
    import app.providers as providers

    seen_editor_prompt = []

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            seen_editor_prompt.append(prompt)
            return "1"
        return "A clever reply that fits this particular situation."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(
        providers.generate(
            "prompt",
            "context",
            language="ur-rom",
            style="desi",
        )
    )
    assert result == "A clever reply that fits this particular situation."
    assert "requested output language is ur-rom" in seen_editor_prompt[0]
    assert "requested humor style is desi" in seen_editor_prompt[0]


def test_provider_rejects_non_text_model_output(monkeypatch):
    import asyncio
    import app.providers as providers

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": {"unexpected": "object"}}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)

    try:
        asyncio.run(providers._complete("prompt", 0.5))
    except providers.ProviderError as exc:
        assert "unexpected response" in str(exc)
    else:
        raise AssertionError("Non-text provider output must be rejected.")
