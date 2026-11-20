import asyncio

import app.providers as providers
from app.prompts import build_prompt


def test_prompt_uses_input_style_and_english():
    prompt = build_prompt("I am always right.", "dry", 2)
    assert "I am always right." in prompt
    assert "understated deadpan" in prompt
    assert "natural contemporary English" in prompt
    assert "5–16 words" in prompt


def test_prompt_has_distinct_angles():
    from app.prompts import ANGLES
    assert len(ANGLES) == 3
    assert len(set(ANGLES)) == 3


def test_desi_style_is_south_asian_humor_written_in_english():
    prompt = build_prompt("He blames the Wi-Fi for every missed deadline.", "desi", 3)
    assert "English-language South Asian social humor" in prompt
    assert "fluent and natural" in prompt


def test_request_defaults():
    from app.schemas import RoastRequest
    request = RoastRequest(text="This is enough context.")
    assert request.style == "instagram"
    assert request.intensity == 3
    assert not hasattr(request, "language")


def test_ranker_penalizes_cliche():
    stale = "Even Google cannot find your personality."
    fresh = "Your confidence arrived early; the evidence missed the train."
    assert providers._quality_score(fresh, "He is always right") > providers._quality_score(stale, "He is always right")


def test_ranker_rewards_contextual_detail():
    contextual = "The 40-slide deck had confidence; the evidence missed every meeting."
    generic = "Your personality is a loading screen with no progress."
    context = "He made a 40-slide presentation about why he is always right."
    assert providers._quality_score(contextual, context) > providers._quality_score(generic, context)


def test_ranker_penalizes_model_preamble():
    assert providers._quality_score("Sure, here is a hilarious roast for you.", "late reply") < 0


def test_ranker_uses_english_tokens():
    assert isinstance(providers._quality_score("The evidence took the day off.", "He is always right."), float)


def test_generate_tolerates_partial_provider_failure(monkeypatch):
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
    assert "STYLE REFERENCE" in prompt
    assert "learn the comic move" in prompt
    assert "never reuse a recognizable phrase" in prompt


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
    seen = []

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            seen.append(prompt)
            return "1"
        if temperature == 0.88:
            return "That 'interesting' reply changed the subject."
        return "The calendar filed a complaint."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate(
        "prompt",
        "He replied 'interesting' and immediately changed the subject.",
        style="desi",
    ))
    assert result == "That 'interesting' reply changed the subject."
    assert "requested humor style is desi" in seen[0]


def test_provider_rejects_non_text_model_output(monkeypatch):
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
    assert "natural, sharp Instagram comment" in prompt
    assert "clean punch" in prompt
    assert "exact situation" in prompt
    assert "transliteration" in prompt


def test_instagram_editor_prioritizes_specific_punchlines(monkeypatch):
    seen = []

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            seen.append(prompt)
            return "1"
        if temperature == 0.88:
            return "The apology got a director's cut. The lateness got four minutes."
        return "The calendar filed a complaint."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate(
        "prompt",
        "He posted a 12-minute apology video for being four minutes late.",
        style="instagram",
    ))
    assert result == "The apology got a director's cut. The lateness got four minutes."
    assert "ACTUAL FUN" in seen[0]
    assert "HUMAN VOICE" in seen[0]


def test_prompt_rejects_unrelated_joke_details():
    prompt = build_prompt(
        "He replied 'interesting' and immediately changed the subject.",
        "instagram",
        3,
    )
    assert "Do not invent a backstory" in prompt
    assert "random analogy" in prompt


def test_instagram_editor_prioritizes_grounding(monkeypatch):
    seen = []

    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            seen.append(prompt)
            return "1"
        if temperature == 0.88:
            return "That 'interesting' reply changed the subject."
        return "The conversation changed lanes without signalling."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    result = asyncio.run(providers.generate(
        "prompt",
        "He replied 'interesting' and immediately changed the subject.",
        style="instagram",
    ))
    assert result == "That 'interesting' reply changed the subject."
    assert "EXACT FIT" in seen[0]
    assert "invented backstory" in seen[0]
    assert "feels effortless and specific" in seen[0]


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


def test_prompt_preserves_exact_numeric_facts():
    prompt = build_prompt(
        "She posted 'no context' and then spent 40 replies explaining the context.",
        "instagram",
        3,
    )
    assert "NUMERIC ACCURACY" in prompt
    assert "40" in prompt
    assert "copy the exact digits and unit" in prompt


def test_prompt_rejects_empty_praise_as_a_punchline():
    prompt = build_prompt("He sent a nine-minute voice note.", "instagram", 3)
    assert "generic judgment" in prompt
    assert "final few words carry the payoff" in prompt


def test_prompt_avoids_quote_markers_in_output():
    prompt = build_prompt("He said 'quick question' and wrote six paragraphs.", "instagram", 3)
    assert "quotation marks" in prompt


def test_prompt_includes_style_voice_sample_without_importing_facts():
    prompt = build_prompt("The fridge is making a strange noise.", "dry", 3)
    assert "VOICE SAMPLE" in prompt
    assert "The reduction has been moved to the next meeting." in prompt
    assert "never reuse its wording, premise, or details" in prompt


def test_each_style_has_its_own_original_anchor():
    from app.prompts import STYLE_ANCHORS
    assert set(STYLE_ANCHORS) == {"instagram", "dry", "desi", "absurd"}
    assert len(set(STYLE_ANCHORS.values())) == 4



def test_voice_sample_uses_real_line_breaks_not_literal_escape_text():
    prompt = build_prompt("The fridge is making a strange noise.", "dry", 3)
    assert "\n\nVOICE SAMPLE" in prompt
    assert "\\nVOICE SAMPLE" not in prompt


def test_prompt_teaches_a_specific_comic_turn_not_generic_roasting():
    prompt = build_prompt("He said he was taking a phone break and replied to every comment.", "instagram", 3)
    assert "social tell" in prompt
    assert "one clean turn" in prompt
    assert "final few words carry the payoff" in prompt
    assert "Casual beats polished" in prompt


def test_prompt_uses_at_most_one_retrieved_example():
    prompt = build_prompt("He sent a quick question and wrote a six-paragraph message.", "instagram", 3)
    assert prompt.count("STYLE REFERENCE") == 1
    assert prompt.count("Comment:") <= 1



def test_prompt_requires_a_real_comic_reinterpretation():
    prompt = build_prompt(
        "He said he was taking a phone break and replied to every comment.",
        "instagram",
        3,
    )
    assert "Change the reader's interpretation" in prompt
    assert "not just rephrase the input" in prompt
    assert "twenty unrelated posts" in prompt
    assert "final few words carry the payoff" in prompt
    assert "Do not invent a backstory" in prompt


def test_prompt_defines_style_specific_humor_without_stereotypes():
    prompt = build_prompt(
        "The family group chat has 86 unread Good morning messages.",
        "desi",
        3,
    )
    assert "English-language South Asian social humor" in prompt
    assert "No generic auntie/uncle/WhatsApp joke" in prompt
    assert "no fake accent" in prompt.lower()


def test_short_action_contexts_accept_one_specific_grounding_anchor():
    assert providers._has_context_anchor(
        "The fridge knows him by name.",
        "He eats a lot.",
    )
    assert providers._has_context_anchor(
        "The fridge knows him by name.",
        "He eats alot.",
    )
    assert providers._has_context_anchor(
        "The silence has started charging for airtime.",
        "He talks a lot.",
    )
    assert not providers._has_context_anchor(
        "The airport has updated its opening hours.",
        "He eats a lot.",
    )


def test_short_food_and_talking_setups_can_reach_the_editor(monkeypatch):
    async def fake_complete(prompt, temperature):
        if "comedy editor" in prompt:
            return "The fridge knows him by name."
        return "The fridge knows him by name."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    food = asyncio.run(providers.generate(
        "Write a short comment.", "He eats a lot.", style="instagram"
    ))
    assert food == "The fridge knows him by name."

    async def talking_complete(prompt, temperature):
        return "The silence has started charging for airtime."

    monkeypatch.setattr(providers, "_complete", talking_complete)
    talking = asyncio.run(providers.generate(
        "Write a short comment.", "He talks a lot.", style="instagram"
    ))
    assert talking == "The silence has started charging for airtime."


def test_spice_level_and_style_playbook_are_explicit():
    from app.prompts import SPICE_LEVELS, STYLE_PLAYBOOK
    assert set(SPICE_LEVELS) == {1, 2, 3, 4, 5}
    assert len(set(STYLE_PLAYBOOK.values())) == 4
    gentle = build_prompt("He eats a lot.", "instagram", 1)
    bold = build_prompt("He eats a lot.", "instagram", 5)
    assert "Gentle" in gentle
    assert "MAXIMUM HEAT" in bold
    assert "Intensity changes the force of the punchline" in bold
    assert "make the punchline sting" in bold
    assert "no mercy for the described behaviour" in providers.SPICE_EDITOR_GUIDANCE[5]
