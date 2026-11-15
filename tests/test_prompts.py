from app.prompts import build_prompt
from app.schemas import RoastRequest
from app.providers import _quality_score

def test_prompt_uses_input_and_style():
    prompt = build_prompt("I am always right.", "en", "dry", 2)
    assert "I am always right." in prompt
    assert "Dry, understated deadpan" in prompt
    assert "5–18 words" in prompt

def test_request_defaults():
    request = RoastRequest(text="This is enough context.")
    assert request.language == "en"
    assert request.style == "instagram"
    assert request.intensity == 3

def test_ranker_penalizes_cliche():
    stale = "Even Google cannot find your personality."
    fresh = "Your confidence arrived early; the evidence missed the train."
    assert _quality_score(fresh, "He is always right") > _quality_score(stale, "He is always right")
