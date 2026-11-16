# COOKED 🔥
### Instagram-comment energy. No AI slop.

COOKED turns a caption, harmless situation, or fictional line into a short, specific English-language comeback. It aims for the rhythm of a great comment-section reply: natural, unexpected, and over before it gets embarrassing.

## Run locally

1. Install [Ollama](https://ollama.com).
2. Pull the default model: `ollama pull qwen2.5:3b`.
3. Install Python 3.10+ and dependencies:

```bash
git clone https://github.com/shaikhabdullahwaseem17-byte/COOKED.git
cd COOKED
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. Open http://127.0.0.1:8000. Keep Ollama running.

COOKED uses an existing instruction model through Ollama. It is **not** a foundation model trained from scratch. Hosted inference is also supported through an OpenAI-compatible endpoint; see `.env.example`.

## What it does

- Supports English output across four distinct humor styles: Instagram, dry, Desi and absurd.
- Desi is a cultural humor style written in natural English, not a separate language mode.
- Retrieves at most one locally curated, original English example when the situation has meaningful overlap with it.
- Generates three distinct comedic approaches concurrently, then asks a separate editor pass to rewrite the drafts into one stronger comment. The editor's output must pass safety, numeric-fact, length, and context-grounding checks; it is not trusted just because the model wrote it.
- Uses a lightweight heuristic as a fallback if the editor fails or returns an invalid choice.
- Penalizes common AI-style preambles, stale templates, overlong outputs and list-like answers; rewards some context anchoring without rewarding simple copying.
- Filters generated comments for exposed contact details, targeted harassment, direct threats, sexual/suggestive material, and medical-condition punchlines. These narrow checks are a guardrail, not comprehensive moderation.
- Requires final comments to remain anchored to details in the original situation and preserve explicit numeric facts. If no safe, fact-consistent, context-grounded line can be produced, the request returns an error rather than inventing a scene.
- Includes one-tap demo prompts and native sharing in the web interface.
- Runs locally by default; no hosted API key is required.

The heuristic ranker is a fallback, not a humor detector. The editor is still an LLM and can make subjective or incorrect choices; neither stage can guarantee that a joke is funny. Output quality depends heavily on the selected model. The lightweight default (`qwen2.5:3b`) has failed the project's initial quality audit and should be treated as a compatibility/demo setting, not as evidence of release-quality humor.

## API

POST `/api/roast`

Example JSON:

```json
{"text":"He said he is the CEO of replying late.","style":"instagram","intensity":3}
```

Styles: `instagram`, `dry`, `desi`, `absurd`. The API has no language selector and prompts for English. Output validation rejects non-Latin scripts, but it is a script check—not a language detector—so non-English text written in Latin letters can still pass. Interactive API docs: http://127.0.0.1:8000/docs.

## Humor principles

1. Specificity beats generic aggression.
2. One punchline, usually 5–16 words.
3. No preamble, explanation, hashtags, emoji spam or forced slang.
4. Avoid tired meme templates and fake internet dialect.
5. Desi humor should feel culturally grounded without forced slang or fake accents.
6. Keep it playful and do not target protected traits, private information or personal vulnerabilities.

## Human evaluation

Run the same fixed cases with the same model version and settings when comparing prompt revisions. The benchmark creates `human-review.csv` with blank rating fields and no model/provider label. Give reviewers that CSV without the metadata-rich JSON/Markdown report, collect independent ratings from at least two people, and follow [`HUMAN_REVIEW.md`](HUMAN_REVIEW.md). Keep individual ratings and safety checks; do not turn the heuristic score into a claim about humor or virality.

## Data provenance

The examples in `data/style_examples.jsonl` are original illustrations written for this repository. They are not scraped Instagram comments. Only contribute material you have permission to redistribute, and document its source and license.

## Development

```bash
pip install -r requirements-dev.txt
pytest -q
PYTHONPATH=. python scripts/humor_benchmark.py
```

## Live benchmark

The GitHub Actions live benchmark runs the fixed, English-only cases against the configured local model and saves a JSON report plus a readable Markdown report as workflow artifacts. The JSON and Markdown reports record all candidate outputs and per-call latency. The workflow also creates a model-blind `human-review.csv` worksheet for independent ratings.

Benchmark situations are kept separate from the curated style examples, with an automated overlap check in the test suite.

Gemma 4 12B is the current live quality challenger. It is not the runtime default unless its actual outputs meet the project's quality bar. Qwen 3.5 9B was previously tested but was too slow and inconsistent for the current workflow. The initial Qwen 2.5 3B benchmark produced only 6 of 8 outputs; the six returned lines were mostly weak, off-context, or unsuitable. See `benchmark-audits/2026-11-16-qwen2.5-3b-output-audit.md`.

The heuristic score is a debugging signal only; it is not a measure of how funny an output is. Follow `HUMAN_REVIEW.md` to score humor, context fit, naturalness, originality and safety. Eight cases are a small diagnostic set and do not establish that comments will perform well on Instagram.

Code is MIT-licensed. The underlying model and third-party datasets retain their own licenses and terms; see MODEL_CARD.md.
