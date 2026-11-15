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
