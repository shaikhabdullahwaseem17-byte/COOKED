# Roadmap

## Available now
- English-only comments and API
- Local generation through Ollama
- Optional OpenAI-compatible provider
- Draft generation, an editor pass and a fallback when needed
- Four styles: Instagram, Dry, Desi (in English) and Absurd
- Local web page and JSON API
- Public browser demo: https://cooked.hazar128373-206.workers.dev/
- Automated Python and browser tests

## Still being worked on
- Better humour, checked by people reviewing real outputs
- Fewer repeated phrases and predictable jokes
- Optional community examples, with clear permission and source details
- Docker setup

The public browser demo is separate from the local Python app. It uses one Cloudflare Workers AI model call per request, while the local app can generate several drafts and use an editor pass.