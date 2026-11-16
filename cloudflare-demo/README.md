# COOKED browser demo

This folder contains the browser version of COOKED. A Cloudflare Worker serves the page and sends comment requests to Cloudflare Workers AI. Visitors do not need to install Python or Ollama, and they do not need their own model API key.

## Current status

The demo is live at:

https://cooked.hazar128373-206.workers.dev/

The live endpoint was checked at `/api/health`, and a comment was generated through the page on 16 November 2026. If you change the browser code, check the Cloudflare deployment page to make sure the new version has actually gone live. A GitHub commit by itself does not prove that Cloudflare has deployed it.

The browser demo is not the same as the local Python app. It makes one Gemma 4 call for each request. The local app can generate several drafts and use a separate editor pass. The two versions can return different results. Neither has been shown to produce consistently excellent humour. People still need to review real outputs.

A parent or guardian must decide whether the hosting arrangement is suitable, own and supervise any Cloudflare account, and review the provider's terms and billing settings. Do not create an account by giving a false age or bypassing an eligibility rule. Do not share account credentials.

## Model, limits and privacy

- Model: `@cf/google/gemma-4-26b-a4b-it`.
- The Worker applies an approximate limit of four generations per minute per IP address. Cloudflare's rate limiter works separately in each Cloudflare location, so this is not a precise global limit.
- Workers AI has a daily free Neuron allowance. The amount used depends on the model and request. Check the current [Workers AI pricing page](https://developers.cloudflare.com/workers-ai/platform/pricing/) and the account dashboard before relying on the free allowance. Do not enable paid usage without the account owner's decision.
- The Worker does not save prompts to a COOKED database or keep an app conversation history. It sends the request to Cloudflare Workers AI, with `store: false` in the model call. This does not mean the request never passes through or is processed by the provider.
- Do not enter names, contact details, private messages or other personal information.

Cloudflare's model details and terms can change. Check the [Gemma 4 model page](https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/) and [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) before making changes.

## Deploy or reconnect it from GitHub

These steps are for the adult account owner or someone they supervise. They are also useful if the current deployment needs to be recreated.

1. Open the [Cloudflare Dashboard](https://dash.cloudflare.com/) and go to **Workers & Pages**.
2. Choose **Create application**, then **GitHub**. Connect this repository and select the `main` branch.
3. Set **Root directory** to the repository root. Leave it blank or use `.`. Do not set it to `cloudflare-demo` when using the command below.
4. Leave the build command empty.
5. Use this deploy command:

   ```sh
   npx wrangler@4.102.0 deploy --config cloudflare-demo/wrangler.jsonc
   ```

   The explicit config path matters because the Wrangler file is inside `cloudflare-demo/`. Its assets directory is `./public`, resolved relative to that config file.
6. The Worker name should be `cooked-public-demo`, as set in `cloudflare-demo/wrangler.jsonc`.
7. Review the account's plan and billing settings before deploying. The repository does not require a paid plan for its current setup.
8. After deployment, open the Worker URL and check `/api/health`. Then generate a comment in the page. Check the Cloudflare deployment history whenever you need to confirm which code is live.

Cloudflare's guide: [Connect a Worker to a GitHub repository](https://developers.cloudflare.com/workers/ci-cd/builds/).

## Run the browser tests

From this folder:

```sh
npm install
npm test
```

The tests use Node's built-in test runner. They check request validation, privacy filters, targeted-abuse checks, prompt construction and output checks. They do not measure whether the model's comments are funny.
