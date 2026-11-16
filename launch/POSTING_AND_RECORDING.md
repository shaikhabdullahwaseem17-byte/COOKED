# COOKED launch material

This is a preparation pack, not a claim that COOKED is already live or that the model is consistently funny. Do not publish a demo link until the browser Worker has actually been deployed and checked.

## What the browser version is

The browser preview is a single-pass Gemma 4 call hosted through Cloudflare Workers AI. It does not use the local Python version's three-draft generation and editor pass. Keep that distinction visible when talking about it.

## Twenty-second screen-recording plan

Record the actual running site on a phone after the public URL is live. Keep the whole browser screen visible; do not add fake output, fake likes, or simulated loading.

| Time | Screen |
|---|---|
| 0–3 sec | Open the real COOKED browser demo. Let the liquid-glass interface sit on screen briefly. |
| 3–7 sec | Paste one ordinary, fictional situation. Example: “He said ‘quick question’ and sent a six-paragraph message.” |
| 7–9 sec | Select Instagram style. Leave spice at 3. |
| 9–12 sec | Tap Write a Comment and keep the real loading state visible. |
| 12–17 sec | Show the comment the live model actually returned. Hold long enough to read it. |
| 17–20 sec | Tap Copy. End on “COOKED — open source. Try it. Break it.” |

Use the first clean, on-topic result from the deployed demo. If it misses, do not quietly replace it with a line written elsewhere and imply it came from the app. Run it again or choose a different setup, and keep the final clip honest.

## Actual output currently on record

One real output from the older local Qwen 2.5 3B diagnostic run:

**Setup:** He said he was taking a break from his phone, then replied to every comment within seconds.

**COOKED output:** “The refresh button won't let him unplug.”

**Review:** The line was on-topic, but the repository's editorial audit called it predictable and not especially original. It is an authentic test result, not a showcase-quality result. Do not use it as proof that COOKED has reached its humour target.

The same audit recorded weak or off-context lines and a safety miss. Those were kept in the audit rather than hidden. Wait for the browser build to be live, collect real outputs from that model, and have people review them before selecting a showcase clip.

## Instagram caption — after a real output is reviewed

COOKED turns a caption or everyday situation into a short comment.

Four styles. One setup. You decide whether the line lands.

It's open source, English-only, and still being tested. Try it, share the result, and tell us when it misses.

[Add the live demo URL only after deployment.]

## Reddit / developer-community post — after deployment

I built COOKED, a small open-source comment writer for captions and everyday situations.

It has four styles: Instagram, dry, Desi and absurd. The browser preview runs without installing Python or a local model. The project also has a local version for people who want to run it themselves.

I'm not claiming it writes viral comments or that every result is funny. The current browser preview is a single-pass model call, and I'm looking for real examples where it sounds generic, misses the context or goes too far.

Try it here: [add the real deployed URL]

If it fails, please share the fictional setup and output with private details removed. The code, tests and contribution guide are public too.

## Ask people to break it

A useful prompt for the community:

> Give COOKED a harmless situation where the funny detail is easy for a person to notice but easy for a model to miss. Share the setup and the actual output. No real names, private conversations or personal details. The best misses become regression tests.

Good feedback should identify one failure: wrong context, invented detail, unnatural phrasing, weak payoff, wrong style or a safety problem.

## Keep the launch honest

- Do not promise likes, virality or a particular humour score.
- Do not use synthetic examples or manually written jokes as if the model generated them.
- Do not hide failures from the benchmark record.
- Do not post private conversations or screenshots that expose personal details.
- Do not claim the browser preview has the same generation pipeline as the local app.
