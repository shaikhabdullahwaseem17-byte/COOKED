# COOKED model integration

COOKED is an English-language humor application and prompt/style layer around an existing instruction-tuned model. Default local integration: Ollama with `qwen2.5:3b` for lightweight compatibility. This default has not met the project's humour target. One eight-case run returned 8/8 outputs, but the comments were weak. A later run returned 6/8, with two generation failures. Both reviews are in `benchmark-audits/`. `gemma4:12b` is being tested as another local option. It has not been shown to be better and is not the default.

This repository does not contain a foundation model trained from random initialization and does not claim the default model was trained by COOKED contributors.

Intended use: playful, consensual humor about fictional situations, ideas and captions. Quality varies by model and context. The output check rejects non-Latin-script letters; it does not identify language, so Latin-script non-English text may pass. It also does not certify grammar, idiom, originality or funniness. A second deterministic candidate filter reuses the private-contact and targeted-harassment checks and rejects several obvious threat, sexual, and suggestive-output patterns before selection. These narrow rules are not comprehensive moderation and cannot guarantee safe output.

The underlying model is downloaded separately and remains subject to its own license and terms.
