# COOKED 🔥
### Instagram-comment energy. No AI slop.

COOKED turns a caption, harmless situation, or fictional line into a short, specific comeback. It aims for the rhythm of a great comment-section reply: natural, unexpected, and over before it gets embarrassing.

## Run locally

1. Install [Ollama](https://ollama.com).
2. Pull the default model: ollama pull qwen2.5:3b
3. Install Python 3.10+ and dependencies:

    git clone https://github.com/shaikhabdullahwaseem17-byte/COOKED.git
    cd COOKED
    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

4. Open http://127.0.0.1:8000. Keep Ollama running.

COOKED uses an existing instruction model through Ollama. It is **not** a foundation model trained from scratch. Hosted inference is also supported through an OpenAI-compatible endpoint; see .env.example.

## What it does

- Retrieves up to two locally curated, original examples matching the requested language and humor style.
- Generates three distinct comedic approaches concurrently, then asks a separate editor pass to choose only among those candidates.
- Uses a Unicode-aware heuristic as a fallback if the editor fails or returns an invalid choice.
- Penalizes common AI-style preambles, stale templates, overlong outputs and list-like answers; rewards some context anchoring without rewarding simple copying.
- Includes one-tap demo prompts and native sharing in the web interface.
- Supports English, Urdu, Roman Urdu and Hindi output modes.
- Offers Instagram, dry, desi and absurd styles.
- Runs locally by default; no hosted API key is required.

The heuristic ranker is a fallback, not a humor detector. The editor is still an LLM and can make subjective or incorrect choices; neither stage can guarantee that a joke is funny. Output quality depends on the model and language; Urdu and Roman Urdu should be judged by fluent speakers.

## API

POST /api/roast

Example JSON:
    {"text":"He said he is the CEO of replying late.","language":"en","style":"instagram","intensity":3}

Languages: en, ur, ur-rom, hi. Styles: instagram, dry, desi, absurd. Interactive API docs: http://127.0.0.1:8000/docs.

## Humor principles

1. Specificity beats generic aggression.
2. One punchline, usually 5–18 words.
3. No preamble, explanation, hashtags, emoji spam or forced slang.
4. Avoid tired meme templates and fake internet dialect.
5. Write naturally in the requested language; don't translate jokes literally.
6. Keep it playful and do not target protected traits, private information or personal vulnerabilities.

## Data provenance

The examples in data/style_examples.jsonl are original illustrations written for this repository. They are not scraped Instagram comments. Only contribute material you have permission to redistribute, and document its source and license.

## Development

    pip install -r requirements-dev.txt
    pytest -q

Code is MIT-licensed. The underlying model and third-party datasets retain their own licenses and terms; see MODEL_CARD.md.
