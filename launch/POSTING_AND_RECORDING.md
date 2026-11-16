# COOKED launch notes

The browser demo is live:

https://cooked.hazar128373-206.workers.dev/

This file contains ideas for showing the real app. It is not a claim that every result is funny or ready to post.

## What the browser demo does

The browser version uses one Gemma 4 call through Cloudflare Workers AI for each request. It does not use the local Python app's draft generation and editor pass. The two versions can return different results.

## Short screen recording

Record the actual site on a phone. Keep the real page and its loading state visible. Do not add fake comments, likes or loading screens.

| Time | What to show |
|---|---|
| 0–3 sec | Open the live COOKED page. |
| 3–7 sec | Enter a harmless, fictional situation. For example: “He said ‘quick question’ and sent a six-paragraph message.” |
| 7–9 sec | Choose Instagram and leave the intensity at 3. |
| 9–12 sec | Tap Roast and show the real loading state. |
| 12–17 sec | Show the comment the app actually returned. |
| 17–20 sec | Use Copy. Leave the COOKED page on screen. |

Use a real result that fits the setup. If the result is weak, do not replace it with a line written by hand and pretend the app made it. Try another setup or leave the miss visible.

## A real result from the local test

This is from an earlier Qwen 2.5 3B test, not from the current browser demo.

**Situation:** He said he was taking a break from his phone, then replied to every comment within seconds.

**Comment:** “The refresh button won't let him unplug.”

**Review:** It fits the situation, but the audit found it predictable and not very original. It is a real test result, not proof that COOKED has reached its humour target.

The audits also record weak results, failed generations and a safety miss. They are kept in the repository so people can see what did not work.

## Short caption

COOKED turns a caption or everyday situation into a short comment.

Choose a style, enter a setup and see what it comes up with. Some results land. Some do not.

It's open source and English-only. Try it and tell me when it gets something wrong.

Demo: https://cooked.hazar128373-206.workers.dev/

## Post for a developer community

I built COOKED, an open-source tool that writes short comments about captions and everyday situations.

It has four styles: Instagram, Dry, Desi and Absurd. The browser version works without installing anything. There is also a local version for people who want to run it themselves.

I'm not claiming it writes viral comments or that every result is funny. The browser version makes one model call per request. I'm looking for examples where it sounds unnatural, misses the situation or goes too far.

Try it: https://cooked.hazar128373-206.workers.dev/

If it gets something wrong, share the fictional setup and the actual output. Remove names and private details first.

## What feedback is useful

A good test is a harmless situation where the important detail is easy for a person to notice but easy for the model to miss. Share the setup and the actual result. Do not include real names, private messages or personal details.

Useful feedback points to one problem: the wrong context, an invented detail, unnatural wording, a weak ending, the wrong style or a safety issue.

## Keep posts honest

- Do not promise likes, virality or a particular humour score.
- Do not show a hand-written joke as if the model generated it.
- Do not hide failed tests or weak outputs.
- Do not post private conversations or screenshots with personal details.
- Do not say the browser demo uses the same generation process as the local app.
