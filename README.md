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
- Retrieves up to two locally curated, original English examples matching the requested humor style.
- Generates three distinct comedic approaches concurrently, then asks a separate editor pass to choose only among those candidates.
- Uses a lightweight heuristic as a fallback if the editor fails or returns an invalid choice.
- Penalizes common AI-style preambles, stale templates, overlong outputs and list-like answers; rewards some context anchoring without rewarding simple copying.
- Includes one-tap demo prompts and native sharing in the web interface.
- Runs locally by default; no hosted API key is required.

The heuristic ranker is a fallback, not a humor detector. The editor is still an LLM and can make subjective or incorrect choices; neither stage can guarantee that a joke is funny. Output quality depends on the selected model.

## API

POST `/api/roast`

Example JSON:

```json
{"text":"He said he is the CEO of replying late.","style":"instagram","intensity":3}
```

Styles: `instagram`, `dry`, `desi`, `absurd`. The API has no language selector and prompts for English. Output validation rejects non-Latin scripts, but it is a script check—not a language detector—so non-English text written in Latin letters can still pass. Interactive API docs: http://127.0.0.1:8000/docs.

## Humor principles

1. Specificity beats generic aggression.
2. One punchline, usually 5–18 words.
3. No preamble, explanation, hashtags, emoji spam or forced slang.
4. Avoid tired meme templates and fake internet dialect.
5. Desi humor should feel culturally grounded without forced slang or fake accents.
6. Keep it playful and do not target protected traits, private information or personal vulnerabilities.

## Data provenance

The examples in `data/style_examples.jsonl` are original illustrations written for this repository. They are not scraped Instagram comments. Only contribute material you have permission to redistribute, and document its source and license.

## Development

```bash
pip install -r requirements-dev.txt
pytest -q
PYTHONPATH=. python scripts/humor_benchmark.py
```

## Live benchmark

The GitHub Actions live benchmark runs the fixed, English-only cases against the configured local model and saves a JSON report plus a readable Markdown report as workflow artifacts. The report records all candidate outputs and per-call latency so that model behaviour can be reviewed rather than judged from a single selected line.

The heuristic score is a debugging signal only; it is not a measure of how funny an output is. Benchmark results require human review and do not establish that comments will perform well on Instagram.

Code is MIT-licensed. The underlying model and third-party datasets retain their own licenses and terms; see MODEL_CARD.md.
