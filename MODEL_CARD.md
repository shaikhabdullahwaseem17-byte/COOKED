# COOKED model integration

COOKED is an English-language humor application and prompt/style layer around an existing instruction-tuned model. Default local integration: Ollama with `qwen2.5:3b`.

This repository does not contain a foundation model trained from random initialization and does not claim the default model was trained by COOKED contributors.

Intended use: playful, consensual humor about fictional situations, ideas and captions. Quality varies by model and context. The output check rejects non-Latin-script letters; it does not identify language, so Latin-script non-English text may pass. It also does not certify grammar, idiom, originality or funniness. A second deterministic candidate filter reuses the private-contact and targeted-harassment checks and rejects several obvious threat and explicit-sexual-content patterns before selection. These narrow rules are not comprehensive moderation and cannot guarantee safe output.

The underlying model is downloaded separately and remains subject to its own license and terms.
