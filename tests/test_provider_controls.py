import asyncio

import pytest

import app.providers as providers


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"content": "A concise comeback."}}


def test_qwen35_candidate_uses_direct_short_output(monkeypatch):
    payloads = []
    timeouts = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            timeouts.append(kwargs.get("timeout"))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            payloads.append(json)
            return _FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.config, "MODEL", "qwen3.5:4b")
    monkeypatch.setattr(providers.config, "REQUEST_TIMEOUT", 180)
    monkeypatch.setattr(providers.httpx, "AsyncClient", _FakeClient)

    result = asyncio.run(providers._complete("Write one short comeback.", 0.9))

    assert result == "A concise comeback."
    assert payloads[0]["think"] is False
    assert payloads[0]["options"]["num_predict"] == 32
    assert timeouts == [180]


def test_qwen35_editor_gets_rewrite_output_budget(monkeypatch):
    payloads = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            payloads.append(json)
            return _FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.config, "MODEL", "qwen3.5:4b")
    monkeypatch.setattr(providers.httpx, "AsyncClient", _FakeClient)

    asyncio.run(providers._complete(
        "You are COOKED's comedy editor. Reply with only the candidate number.",
        0.12,
    ))

    assert payloads[0]["think"] is False
    assert payloads[0]["options"]["num_predict"] == 48


def test_other_ollama_models_keep_existing_generation_controls(monkeypatch):
    payloads = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            payloads.append(json)
            return _FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.config, "MODEL", "qwen2.5:7b")
    monkeypatch.setattr(providers.httpx, "AsyncClient", _FakeClient)

    asyncio.run(providers._complete("Write one short comeback.", 0.9))

    assert "think" not in payloads[0]
    assert "num_predict" not in payloads[0]["options"]


def test_candidate_shape_filter_rejects_hashtags_runons_and_filler():
    too_long = "a " * 23
    assert not providers._is_usable_candidate(too_long)
    assert not providers._is_usable_candidate('This "quote is never closed.')
    assert not providers._is_usable_candidate(
        "A brief joke with padding. #MetaCommentary #PlotTwist"
    )
    assert not providers._is_usable_candidate(
        "This is a line.\nThis is a second line."
    )
    assert not providers._is_usable_candidate(
        "This is just kidding and then wait, actually the joke changes again."
    )


def test_candidate_shape_filter_accepts_a_short_grounded_comment():
    assert providers._is_usable_candidate(
        "His ETA is apparently measured in outfit changes."
    )


def test_gemma4_uses_fast_thinking_mode_and_bounded_output(monkeypatch):
    payloads = []
    timeouts = []

    class _GemmaResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "One concise comment."}}

    class _GemmaClient:
        def __init__(self, *args, **kwargs):
            timeouts.append(kwargs.get("timeout"))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            payloads.append(json)
            return _GemmaResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.config, "MODEL", "gemma4:e2b")
    monkeypatch.setattr(providers.config, "REQUEST_TIMEOUT", 180)
    monkeypatch.setattr(providers.httpx, "AsyncClient", _GemmaClient)

    result = asyncio.run(providers._complete("Write one concise comment.", 0.9))

    assert result == "One concise comment."
    assert payloads[0]["think"] is False
    assert payloads[0]["options"]["num_predict"] == 32
    assert timeouts == [90]


def test_fact_consistency_rejects_changed_explicit_numbers():
    context = "She spent 40 replies explaining the context."
    assert not providers._is_fact_consistent_candidate(
        "Four responses later, the story still needed explaining.", context
    )
    assert providers._is_fact_consistent_candidate(
        "Forty replies later, the story still needed explaining.", context
    )
    assert providers._is_fact_consistent_candidate(
        "The explanation became its own discussion.", context
    )


def test_numeric_extraction_does_not_read_numbers_inside_words():
    context = "He replied to 40 comments on his phone."
    assert providers._is_fact_consistent_candidate(
        "His phone was still getting notifications.", context
    )


def test_candidate_filter_rejects_generic_praise_endings():
    for candidate in (
        "Nine minutes for a quick thought? That's commitment.",
        "Ninety minutes for meetings? Peak efficiency.",
        "That's a whole other kind of mood board.",
    ):
        assert not providers._is_usable_candidate(candidate)


def test_candidate_filter_keeps_specific_punchlines():
    assert providers._is_usable_candidate(
        "The question arrived with supporting documentation."
    )


def test_style_editor_guidance_exists_for_every_style():
    assert set(providers.STYLE_EDITOR_GUIDANCE) == {
        "instagram", "dry", "desi", "absurd"
    }


def test_candidate_filter_rejects_generic_praise_and_metaphor_words():
    for candidate in (
        "Taking a break but replying instantly is a whole new level of commitment.",
        "Forty replies for no context? That's a whole thesis.",
        "A tiny update turned into a 23-message novel.",
        "Ninety minutes for cutting meetings? That's practically a full day.",
        "86 greetings means someone is hitting send on auto-pilot.",
    ):
        assert not providers._is_usable_candidate(candidate)


def test_single_valid_candidate_still_gets_a_comedy_rewrite(monkeypatch):
    calls = []

    async def fake_complete(prompt, temperature):
        calls.append(prompt)
        if "You are COOKED's comedy editor" in prompt:
            return "The calendar has rescheduled itself again."
        if temperature == 0.88:
            return "The calendar filed a complaint."
        return "That's commitment."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate(
        "Write one short comment.", "He changed the meeting time again.", "instagram"
    ))

    assert result == "The calendar has rescheduled itself again."
    assert len(calls) == 4



def test_generate_rejects_candidates_that_fail_output_safety(monkeypatch):
    async def fake_complete(prompt, temperature):
        if temperature == 0.88:
            return "Mock her because she has depression."
        return "That's commitment."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    with pytest.raises(providers.ProviderError, match="No usable"):
        asyncio.run(providers.generate(
            "Write one short comment.",
            "A harmless situation.",
            "instagram",
        ))
