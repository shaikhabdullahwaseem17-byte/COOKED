import asyncio

from scripts.humor_benchmark import CASES, run_case


def test_benchmark_covers_english_and_all_styles():
    assert all(case["id"].startswith("en_") for case in CASES)
    assert {case["style"] for case in CASES} == {"instagram", "dry", "desi", "absurd"}
    assert len(CASES) == 8
    assert len({case["id"] for case in CASES}) == len(CASES)


def test_benchmark_records_candidate_and_editor_flow(monkeypatch):
    import app.providers as providers

    async def fake_complete(prompt, temperature):
        if "COOKED's comedy editor" in prompt:
            return "2"
        if temperature == 0.88:
            return "The apology had a longer runtime than the delay."
        if temperature == 0.98:
            return "Four minutes late, twelve minutes of director's commentary."
        return "A clock called; it wants its time back."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    case = {
        "id": "test_case",
        "style": "instagram",
        "text": "He posted a 12-minute apology video for being four minutes late.",
    }
    result = asyncio.run(run_case(case))
    assert result["answer"] == "Four minutes late, twelve minutes of director's commentary."
    assert len(result["candidate_outputs"]) == 3
    assert result["editor_output"] == "2"
    assert result["selected_candidate_index"] == 2
    assert result["failure"] is None
