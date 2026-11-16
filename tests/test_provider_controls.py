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
    assert timeouts == [180]


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
    with pytest.raises(providers.ProviderError, match="No safe, fact-consistent"):
        asyncio.run(providers.generate(
            "Write one short comment.",
            "A harmless situation.",
            "instagram",
        ))

def test_one_sunrise_idiom_does_not_trigger_false_numeric_mismatch():
    context = (
        "The family group chat has 86 unread messages, all forwarding "
        "the same Good morning greeting."
    )
    assert providers._is_fact_consistent_candidate(
        "One sunrise, 86 identical greetings.", context
    )


def test_spelled_out_measurements_still_protect_explicit_counts():
    context = "He described a nine-minute voice note as a quick thought."
    assert not providers._is_fact_consistent_candidate(
        "Two minutes for a quick thought?", context
    )


def test_all_ages_output_guard_rejects_suggestive_clothing_jokes():
    from app.safety import is_safe_output

    assert not is_safe_output(
        "That is a teeny-tiny update? More like a maxi-panties reveal!"
    )
    assert not is_safe_output("The joke turned into an underwear reference.")
    assert is_safe_output("The update has its own notification schedule.")



def test_context_anchor_guard_rejects_unrelated_or_invented_scenes():
    assert not providers._has_context_anchor(
        "No context? It is like playing hide and seek with your eyes closed.",
        "She posted no context and spent 40 replies explaining the context.",
    )
    assert not providers._has_context_anchor(
        "That is basically next door unless I am late to my own wedding.",
        "He described a 35-minute drive as basically next door.",
    )
    assert not providers._has_context_anchor(
        "The fern demands its very own jungle terrarium.",
        "She made a color-coded seating chart for the houseplants.",
    )


def test_context_anchor_guard_keeps_specific_reframes():
    assert providers._has_context_anchor(
        "The refresh button will not let him unplug.",
        "He said he was taking a break from his phone, then replied to every comment within seconds.",
    )
    assert providers._has_context_anchor(
        "That thought came with a nine-minute runtime.",
        "He described a nine-minute voice note as just a quick thought.",
    )


def test_editor_can_rewrite_long_safe_drafts_that_fail_shape_validation(monkeypatch):
    async def fake_complete(prompt, temperature):
        if "You are COOKED's comedy editor" in prompt:
            return "That thought came with a nine-minute runtime."
        return (
            "He called the voice note quick, although it contains far too much "
            "explanation and a very long description of the same thought."
        )

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate(
        "Write one short comment.",
        "He described a nine-minute voice note as just a quick thought.",
        style="instagram",
    ))
    assert result == "That thought came with a nine-minute runtime."
