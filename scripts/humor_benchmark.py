"""Run COOKED's English-only live humor benchmark."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import config, providers
from app.prompts import build_prompt

CASES: tuple[dict[str, str], ...] = (
    # Five fresh Instagram cases: deliberately distinct from the style-reference inputs.
    {"id": "en_instagram_voice_note", "style": "instagram", "text": "He described a nine-minute voice note as 'just a quick thought'."},
    {"id": "en_instagram_no_context", "style": "instagram", "text": "She posted 'no context' and then spent 40 replies explaining the context."},
    {"id": "en_instagram_effortless_caption", "style": "instagram", "text": "He called the caption 'effortless' after rewriting it nineteen times."},
    {"id": "en_instagram_phone_break", "style": "instagram", "text": "He said he was taking a break from his phone, then replied to every comment within seconds."},
    {"id": "en_instagram_tiny_update", "style": "instagram", "text": "She promised a 'tiny update' and posted a 23-message thread."},
    {"id": "en_dry_meeting", "style": "dry", "text": "The recurring meeting to discuss cutting meetings has been extended to 90 minutes."},
    {"id": "en_desi_group_chat", "style": "desi", "text": "The family group chat has 86 unread messages, all forwarding the same 'Good morning' greeting."},
    {"id": "en_absurd_plants", "style": "absurd", "text": "She made a color-coded seating chart for the houseplants."},
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
        if (
            is_valid_output(output)
            and providers._is_usable_candidate(output)
            and providers._is_fact_consistent_candidate(output, case["text"])
            and output not in seen
        ):
            seen.add(output)
            candidates.append(output)
    editor = [c for c in calls if c["kind"] == "editor"]
    selected = candidates.index(answer) + 1 if answer in candidates else None
    editor_output = editor[-1].get("output") if editor else None
    editor_choice = None
    if editor_output:
        match = re.fullmatch(r"\s*([1-9]\d*)\s*", editor_output)
        if match:
            editor_choice = int(match.group(1))
    if len(candidates) == 1 and answer == candidates[0]:
        selection_method = "single_candidate"
    elif selected is not None and editor_choice == selected:
        selection_method = "editor"
    else:
        selection_method = "heuristic_fallback"
    return {
        **case, "language": "en", "answer": answer, "failure": failure,
        "candidate_outputs": candidates,
        "editor_output": editor_output,
        "selection_method": selection_method,
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
            f"**Candidate selection:** {row['selected_candidate_index'] or 'fallback / unavailable'} ({row['selection_method']})", "",
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
