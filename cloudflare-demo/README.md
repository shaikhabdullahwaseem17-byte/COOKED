# COOKED browser demo

This folder contains the browser version of COOKED. It serves the same liquid-glass interface from a Cloudflare Worker and calls Cloudflare Workers AI from the server. Visitors do not install Python or Ollama and do not need an API key.

## Status

The code is prepared, but **the public URL does not exist until a Cloudflare account owner deploys it**. The app is not being described as live before that happens.

This is a public-preview backend, not a byte-for-byte copy of the local Python generation pipeline. It uses one carefully prompted Gemma 4 call per request rather than the local app's multiple drafts and editor pass. Its humour quality still needs real blind human review.

This code is ready for an adult account owner to review and deploy. Cloudflare's privacy policy says its own services are not designed to attract people under 18. A parent or guardian must decide whether this hosting arrangement is appropriate, own and supervise any account, and review the terms and privacy obligations. Do not create an account by misrepresenting age or bypassing an eligibility rule.

## Model and limits

- Model: `@cf/google/gemma-4-26b-a4b-it`.
- Cloudflare currently lists this model as Cloudflare-hosted with zero data retention.
- The Worker Free plan currently includes 10,000 AI Neurons per day. Once that allowance is used, new generations fail until the daily reset. Do not enable a paid plan for this initial demo.
- The app also applies an approximate four-generation-per-minute rate limit per IP address. Cloudflare says this rate limiter is approximate and operates separately in each Cloudflare location.
- The demo does not have a prompt database, login system, analytics database or persistent conversation history. The request is processed by Cloudflare Workers AI. Avoid entering names, contact information or private conversations.

These provider limits and terms can change; check the linked Cloudflare pages before launch:
- [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Gemma 4 26B model details](https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/)
- [Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/)

## Deploy from GitHub (dashboard method)

Cloudflare's Git integration supports deploying Workers from a GitHub repository. A parent or guardian should own and supervise the Cloudflare account and review the provider terms and billing settings. Do not share account credentials.

1. Have the adult account owner open [Cloudflare Dashboard](https://dash.cloudflare.com/) and go to **Workers & Pages**.
2. Select **Create application**, then **GitHub**. Connect the COOKED repository and choose the `main` branch.
3. Set **Root directory** to the repository root (leave it blank/default, or use `.`). Do not set it to `cloudflare-demo` for this command.
4. Leave the optional build command empty.
5. Set the **Deploy command** exactly to:

   ```sh
   npx wrangler@4.102.0 deploy --config cloudflare-demo/wrangler.jsonc
   ```

   This explicitly selects the demo's Wrangler configuration. The failed build log shows Cloudflare ran `npx wrangler deploy` from the repository root, where it did not find `cloudflare-demo/wrangler.jsonc`; it then tried to treat the project as a static-assets project and could not find the expected directory. The explicit `--config` path fixes that configuration lookup. The assets directory in the config is `./public`, resolved relative to the config file.
6. Make sure the Worker name is `cooked-public-demo`, matching `cloudflare-demo/wrangler.jsonc`.
7. Keep the account on the **Workers Free** plan for this trial. Do not opt into paid usage or add a paid billing plan for the demo.
8. Save and deploy. Cloudflare will provide a `workers.dev` URL.
9. Open the URL and check `/api/health`. It should return a JSON status and the model ID. Then test one example in the page.

Cloudflare's documentation: [Connect a Worker to a GitHub repository](https://developers.cloudflare.com/workers/ci-cd/builds/).

## Tests

From this folder, run:

```sh
npm install
npm test
```

The test suite uses Node's built-in test runner. It checks input validation, privacy filters, targeted-abuse rejection, prompt construction and final-output checks. It does not test model humour quality.
