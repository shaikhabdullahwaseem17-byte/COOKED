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
    assert result["selection_method"] == "editor"
    assert result["failure"] is None


def test_benchmark_cases_do_not_duplicate_style_references():
    import re
    from app.examples import load_examples

    def terms(text):
        return {
            token for token in re.findall(r"[^\\W_]+", text.casefold())
            if len(token) > 2
        }

    for case in CASES:
        benchmark_terms = terms(case["text"])
        for example in load_examples():
            if example["style"] != case["style"]:
                continue
            example_terms = terms(example["input"])
            union = benchmark_terms | example_terms
            overlap = len(benchmark_terms & example_terms) / len(union)
            assert case["text"].casefold() != example["input"].casefold()
            assert overlap < 0.6, (
                f"{case['id']} is too close to a style example: {example['input']}"
            )


def test_benchmark_reports_single_candidate_without_editor(monkeypatch):
    import app.providers as providers

    async def fake_complete(prompt, temperature):
        if "You are COOKED's comedy editor" in prompt:
            raise AssertionError("Single candidate should not call the editor")
        if temperature == 0.88:
            return "The calendar filed a complaint."
        return "That's commitment."

    monkeypatch.setattr(providers, "_complete", fake_complete)
    case = {
        "id": "single_candidate",
        "style": "instagram",
        "text": "He changed the meeting time again.",
    }
    result = asyncio.run(run_case(case))
    assert result["answer"] == "The calendar filed a complaint."
    assert result["editor_output"] is None
    assert result["selection_method"] == "single_candidate"
