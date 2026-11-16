# Contributing

Help make COOKED funnier, more natural and more useful. The best contributions are specific and testable.

## Good first contributions

- Add an original English-language test situation with a clear comic angle.
- Improve a line that feels translated, scripted or generic.
- Add a regression test for a context miss, invented fact or safety failure.
- Improve mobile layout, keyboard use or screen-reader feedback.
- Report when a style does not sound like the style it claims to be.

## Before opening a pull request

1. Explain the problem in one paragraph.
2. Include a before/after example when the change affects generated comments.
3. Keep the joke about a situation or choice—not a person's identity, appearance, disability, health, trauma or private life.
4. Add a test for bug fixes and prompt regressions.
5. Run the relevant tests and say exactly what you ran.

For the Python app:

```sh
pip install -r requirements-dev.txt
pytest -q
```

For the browser demo:

```sh
cd cloudflare-demo
npm install
npm test
```

## Example contributions

Original situations and comments are welcome, but only submit writing you created or have permission to redistribute. Do not scrape Instagram comments. Do not include real names, contact details, private conversations, or identifying information.

## Feedback

Use [Discussions](https://github.com/shaikhabdullahwaseem17-byte/COOKED/discussions) for jokes, examples, model misses and ideas. Use [Issues](https://github.com/shaikhabdullahwaseem17-byte/COOKED/issues) for reproducible bugs. A good bug report includes the setup, chosen style, output, and what was wrong—after removing private details.
