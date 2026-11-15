import asyncio

import app.providers as providers


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"content": "A concise comeback."}}


def test_qwen35_candidate_uses_direct_short_output(monkeypatch):
    payloads = []
    timeouts = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            timeouts.append(kwargs.get("timeout"))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            payloads.append(json)
            return _FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.config, "MODEL", "qwen3.5:4b")
    monkeypatch.setattr(providers.config, "REQUEST_TIMEOUT", 180)
    monkeypatch.setattr(providers.httpx, "AsyncClient", _FakeClient)

    result = asyncio.run(providers._complete("Write one short comeback.", 0.9))

    assert result == "A concise comeback."
    assert payloads[0]["think"] is False
    assert payloads[0]["options"]["num_predict"] == 48
    assert timeouts == [90]


def test_qwen35_editor_gets_tiny_output_budget(monkeypatch):
    payloads = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            payloads.append(json)
            return _FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.config, "MODEL", "qwen3.5:4b")
    monkeypatch.setattr(providers.httpx, "AsyncClient", _FakeClient)

    asyncio.run(providers._complete(
        "You are COOKED's comedy editor. Reply with only the candidate number.",
        0.12,
    ))

    assert payloads[0]["think"] is False
    assert payloads[0]["options"]["num_predict"] == 6


def test_other_ollama_models_keep_existing_generation_controls(monkeypatch):
    payloads = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            payloads.append(json)
            return _FakeResponse()

    monkeypatch.setattr(providers.config, "PROVIDER", "ollama")
    monkeypatch.setattr(providers.config, "MODEL", "qwen2.5:7b")
    monkeypatch.setattr(providers.httpx, "AsyncClient", _FakeClient)

    asyncio.run(providers._complete("Write one short comeback.", 0.9))

    assert "think" not in payloads[0]
    assert "num_predict" not in payloads[0]["options"]


def test_candidate_shape_filter_rejects_hashtags_runons_and_filler():
    too_long = "a " * 23
    assert not providers._is_usable_candidate(too_long)
    assert not providers._is_usable_candidate('This "quote is never closed.')
    assert not providers._is_usable_candidate(
        "A brief joke with padding. #MetaCommentary #PlotTwist"
    )
    assert not providers._is_usable_candidate(
        "This is a line.\nThis is a second line."
    )
    assert not providers._is_usable_candidate(
        "This is just kidding and then wait, actually the joke changes again."
    )


def test_candidate_shape_filter_accepts_a_short_grounded_comment():
    assert providers._is_usable_candidate(
        "His ETA is apparently measured in outfit changes."
    )
