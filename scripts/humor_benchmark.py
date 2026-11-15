"""Run COOKED's live humor benchmark against the configured model.

This records real model outputs and selection decisions. It deliberately does not
pretend that an automated heuristic is a reliable measure of human funniness.
"""
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
    {
        "id": "en_instagram_01",
        "language": "en",
        "style": "instagram",
        "text": "He posted a 12-minute apology video for being four minutes late.",
    },
    {
        "id": "en_dry_01",
        "language": "en",
        "style": "dry",
        "text": "My friend made a spreadsheet to decide what to eat for lunch, then ordered the exact same thing as always.",
    },
    {
        "id": "en_absurd_01",
        "language": "en",
        "style": "absurd",
        "text": "She packed three suitcases for a one-night trip.",
    },
    {
        "id": "en_des i_01".replace(" ", ""),
        "language": "en",
        "style": "desi",
        "text": "He says 'I'm two minutes away' while he is still deciding what to wear.",
    },
    {
        "id": "roman_urdu_desi_01",
        "language": "ur-rom",
        "style": "desi",
        "text": "Woh har group project mein kehta hai main sab sambhal lunga, phir deadline par 'net issue tha' bolta hai.",
    },
    {
        "id": "urdu_desi_01",
        "language": "ur",
        "style": "desi",
        "text": "وہ ہر بات پر مشورہ دیتا ہے، مگر اپنے فیصلے ہمیشہ دوسروں سے پوچھ کر کرتا ہے۔",
    },
    {
        "id": "hindi_dry_01",
        "language": "hi",
        "style": "dry",
        "text": "वह हर मीटिंग में कहता है कि बात छोटी रखेंगे, फिर सबसे लंबा बोलता है।",
    },
    {
        "id": "en_instagram_low_context",
        "language": "en",
        "style": "instagram",
        "text": "He replied 'interesting' and immediately changed the subject.",
    },
)


async def run_case(case: dict[str, str]) -> dict[str, Any]:
    recorded_calls: list[dict[str, Any]] = []
    original_complete = providers._complete

    async def recording_complete(prompt: str, temperature: float) -> str:
        started = time.perf_counter()
        kind = "editor" if "COOKED's comedy editor" in prompt else "candidate"
        try:
            result = await original_complete(prompt, temperature)
        except Exception as exc:
            recorded_calls.append(
                {
                    "kind": kind,
                    "temperature": temperature,
                    "error": f"{type(exc).__name__}: {exc}",
                    "latency_seconds": round(time.perf_counter() - started, 3),
                }
            )
            raise
        recorded_calls.append(
            {
                "kind": kind,
                "temperature": temperature,
                "output": result,
                "latency_seconds": round(time.perf_counter() - started, 3),
            }
        )
        return result

    providers._complete = recording_complete
    started = time.perf_counter()
    try:
        prompt = build_prompt(
            case["text"], case["language"], case["style"], intensity=3
        )
        answer = await providers.generate(
            prompt,
            case["text"],
            language=case["language"],
            style=case["style"],
        )
    except Exception as exc:
        answer = None
        failure = f"{type(exc).__name__}: {exc}"
    else:
        failure = None
    finally:
        providers._complete = original_complete

    raw_candidates = [
        item for item in recorded_calls if item["kind"] == "candidate"
    ]
    raw_candidates.sort(key=lambda item: item["temperature"])
    # The editor sees deduplicated candidates, so report its index in that
    # same list rather than the raw call list (which may contain duplicates).
    candidates = []
    seen = set()
    for item in raw_candidates:
        output = item.get("output")
        if output and output not in seen:
            seen.add(output)
            candidates.append(item)
    editor_calls = [item for item in recorded_calls if item["kind"] == "editor"]
    selected_index = None
    if answer is not None:
        for index, item in enumerate(candidates, start=1):
            if item.get("output") == answer:
                selected_index = index
                break

    return {
        **case,
        "answer": answer,
        "failure": failure,
        "candidate_outputs": [item.get("output") for item in candidates],
        "candidate_errors": [item.get("error") for item in candidates if "error" in item],
        "editor_output": editor_calls[-1].get("output") if editor_calls else None,
        "selected_candidate_index": selected_index,
        "heuristic_score": (
            providers._quality_score(answer, case["text"])
            if answer is not None
            else None
        ),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "model": config.MODEL if config.PROVIDER == "ollama" else config.OPENAI_MODEL,
        "provider": config.PROVIDER,
        "calls": recorded_calls,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# COOKED live humor benchmark",
        "",
        f"- Run UTC: {report['run_utc']}",
        f"- Provider: {report['provider']}",
        f"- Model: {report['model']}",
        f"- Cases: {len(report['results'])}",
        f"- Successful outputs: {sum(bool(row['answer']) for row in report['results'])}",
        "",
        "> The heuristic score is a debugging signal, not a humor score. "
        "Outputs require human review; this benchmark does not claim an objective "
        "or statistically validated funniness measurement.",
        "",
    ]
    for row in report["results"]:
        lines.extend(
            [
                f"## {row['id']} — {row['language']} / {row['style']}",
                "",
                f"**Input:** {row['text']}",
                "",
                f"**COOKED output:** {row['answer'] or '[FAILED]'}",
                "",
                f"**Candidate selection:** {row['selected_candidate_index'] or 'fallback / unavailable'}",
                "",
            ]
        )
        for index, candidate in enumerate(row["candidate_outputs"], start=1):
            lines.append(f"- Candidate {index}: {candidate}")
        if row["editor_output"]:
            lines.extend(["", f"**Editor response:** {row['editor_output']}"])
        if row["failure"]:
            lines.extend(["", f"**Failure:** {row['failure']}"])
        lines.extend(["", f"Elapsed: {row['elapsed_seconds']} s", ""])
    return "\n".join(lines)


async def main(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for case in CASES:
        print(f"\n=== {case['id']} | {case['language']} / {case['style']} ===", flush=True)
        result = await run_case(case)
        results.append(result)
        print(f"INPUT: {result['text']}", flush=True)
        for index, candidate in enumerate(result["candidate_outputs"], start=1):
            print(f"CANDIDATE {index}: {candidate}", flush=True)
        print(f"EDITOR: {result['editor_output']}", flush=True)
        print(f"FINAL: {result['answer']}", flush=True)
        if result["failure"]:
            print(f"FAILURE: {result['failure']}", flush=True)

    report = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "provider": config.PROVIDER,
        "model": config.MODEL if config.PROVIDER == "ollama" else config.OPENAI_MODEL,
        "temperature_candidates": [0.88, 0.98, 1.05],
        "case_count": len(CASES),
        "results": results,
    }
    json_path = output_dir / "humor-benchmark.json"
    markdown_path = output_dir / "humor-benchmark.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    successes = sum(bool(row["answer"]) for row in results)
    print(f"\nSaved {json_path} and {markdown_path}", flush=True)
    print(f"SUMMARY: {successes}/{len(results)} cases produced an output.", flush=True)
    return 0 if successes == len(results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark-results"),
        help="Directory for JSON and Markdown benchmark output.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.output_dir)))
