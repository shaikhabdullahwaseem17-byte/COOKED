"""Run COOKED's English-only live humor benchmark."""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import config, providers
from app.prompts import build_prompt

CASES: tuple[dict[str, str], ...] = (
    {"id": "en_instagram_apology", "style": "instagram", "text": "He posted a 12-minute apology video for being four minutes late."},
    {"id": "en_dry_lunch", "style": "dry", "text": "My friend made a spreadsheet to decide what to eat for lunch, then ordered the exact same thing as always."},
    {"id": "en_absurd_luggage", "style": "absurd", "text": "She packed three suitcases for a one-night trip."},
    {"id": "en_desi_late", "style": "desi", "text": "He says 'I'm two minutes away' while he is still deciding what to wear."},
    {"id": "en_instagram_low_context", "style": "instagram", "text": "He replied 'interesting' and immediately changed the subject."},
    {"id": "en_dry_meeting", "style": "dry", "text": "He says every meeting will be brief, then speaks longer than everyone else."},
    {"id": "en_absurd_overplanning", "style": "absurd", "text": "She made a 14-step plan for a five-minute errand."},
    {"id": "en_desi_group_project", "style": "desi", "text": "He volunteers to handle every group project, then blames the internet at the deadline."},
)


async def run_case(case: dict[str, str]) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    original = providers._complete

    async def recording(prompt: str, temperature: float) -> str:
        started = time.perf_counter()
        kind = "editor" if "COOKED's comedy editor" in prompt else "candidate"
        try:
            output = await original(prompt, temperature)
            calls.append({"kind": kind, "temperature": temperature, "output": output,
                          "latency_seconds": round(time.perf_counter() - started, 3)})
            return output
        except Exception as exc:
            calls.append({"kind": kind, "temperature": temperature,
                          "error": f"{type(exc).__name__}: {exc}",
                          "latency_seconds": round(time.perf_counter() - started, 3)})
            raise

    providers._complete = recording
    started = time.perf_counter()
    try:
        prompt = build_prompt(case["text"], case["style"], 3)
        answer = await providers.generate(prompt, case["text"], style=case["style"])
        failure = None
    except Exception as exc:
        answer, failure = None, f"{type(exc).__name__}: {exc}"
    finally:
        providers._complete = original

    from app.output_validation import is_valid_output
    candidates, seen = [], set()
    for call in sorted((c for c in calls if c["kind"] == "candidate" and "output" in c),
                       key=lambda c: c["temperature"]):
        output = call["output"].strip()
        if is_valid_output(output) and output not in seen:
            seen.add(output)
            candidates.append(output)
    editor = [c for c in calls if c["kind"] == "editor"]
    selected = candidates.index(answer) + 1 if answer in candidates else None
    return {
        **case, "language": "en", "answer": answer, "failure": failure,
        "candidate_outputs": candidates,
        "editor_output": editor[-1].get("output") if editor else None,
        "selected_candidate_index": selected,
        "heuristic_score": providers._quality_score(answer, case["text"]) if answer else None,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "provider": config.PROVIDER,
        "model": config.MODEL if config.PROVIDER == "ollama" else config.OPENAI_MODEL,
        "calls": calls,
    }


def render_markdown(report: dict[str, Any]) -> str:
    successes = sum(bool(row["answer"]) for row in report["results"])
    lines = [
        "# COOKED live humor benchmark", "",
        f"- Run UTC: {report['run_utc']}",
        f"- Provider: {report['provider']}",
        f"- Model: {report['model']}",
        f"- Cases: {len(report['results'])}",
        f"- Successful outputs: {successes}", "",
        "> The heuristic score is a debugging signal, not a humor score. Human review is required.", "",
    ]
    for row in report["results"]:
        lines += [
            f"## {row['id']} — English / {row['style']}", "",
            f"**Input:** {row['text']}", "",
            f"**COOKED output:** {row['answer'] or '[FAILED]'}", "",
            f"**Candidate selection:** {row['selected_candidate_index'] or 'fallback / unavailable'}", "",
        ]
        lines += [f"- Candidate {i}: {candidate}" for i, candidate in enumerate(row["candidate_outputs"], 1)]
        if row["editor_output"]:
            lines += ["", f"**Editor response:** {row['editor_output']}"]
        if row["failure"]:
            lines += ["", f"**Failure:** {row['failure']}"]
        lines += ["", f"Elapsed: {row['elapsed_seconds']} s", ""]
    return "\n".join(lines)


async def main(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for case in CASES:
        print(f"\n=== {case['id']} | English / {case['style']} ===", flush=True)
        result = await run_case(case)
        results.append(result)
        print(f"FINAL: {result['answer']}", flush=True)
        if result["failure"]:
            print(f"FAILURE: {result['failure']}", flush=True)
    report = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "provider": config.PROVIDER,
        "model": config.MODEL if config.PROVIDER == "ollama" else config.OPENAI_MODEL,
        "case_count": len(CASES), "results": results,
    }
    (output_dir / "humor-benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "humor-benchmark.md").write_text(render_markdown(report), encoding="utf-8")
    successes = sum(bool(row["answer"]) for row in results)
    print(f"\nSUMMARY: {successes}/{len(results)} cases produced an output.", flush=True)
    return 0 if successes == len(results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark-results"))
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.output_dir)))
