# COOKED 🔥
### Instagram-comment energy. No AI slop.

COOKED turns context into short, specific, internet-native comebacks. The goal is the timing of a great comment-section reply: natural, surprising, and over before it gets embarrassing.

## Run locally
1. Install [Ollama](https://ollama.com).
2. Run `ollama pull qwen2.5:3b`.
3. Install Python 3.10+.
4. Run:

```bash
git clone https://github.com/shaikhabdullahwaseem17-byte/COOKED.git
cd COOKED
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Keep Ollama running.

COOKED uses an existing instruction model through Ollama. It is **not** a foundation model trained from scratch. Hosted inference is also supported through an OpenAI-compatible endpoint; see `.env.example`.

## Features
- Candidate generation from three distinct comedic angles, followed by heuristic ranking.
- English, Urdu, Roman Urdu and Hindi output modes.
- Instagram, dry, desi and absurd humor styles.
- Local inference by default; no hosted API key required.
- FastAPI JSON endpoint and responsive web interface.

## API
`POST /api/roast`

```json
{"text":"He said he is the CEO of replying late.","language":"en","style":"instagram","intensity":3}
```

Languages: `en`, `ur`, `ur-rom`, `hi`. Styles: `instagram`, `dry`, `desi`, `absurd`. Interactive docs: http://127.0.0.1:8000/docs

## Quality principles
- One punchline, usually 5–18 words.
- Use a specific detail or contradiction from the context.
- No preamble, explanation, hashtags, emoji spam or forced slang.
- Avoid stale templates and generic "AI savage" lines.
- Write naturally in the requested language; don't translate jokes literally.

The ranker is a lightweight heuristic, not a guarantee of humor. Actual quality depends on the selected model and language.

## Safety and data
Use for playful banter about fictional situations, ideas, captions and consenting friends. Don't target protected traits, private information or personal vulnerabilities. Don't paste private conversations or personal data.

The included examples are original illustrations, not scraped Instagram comments. Only contribute material you have rights to use and document provenance.

## Development
```bash
pip install -r requirements-dev.txt
pytest
```

Code is MIT-licensed. Underlying model and third-party dataset terms remain separate; see [MODEL_CARD.md](MODEL_CARD.md).