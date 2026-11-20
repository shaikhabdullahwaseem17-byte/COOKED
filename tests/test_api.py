import asyncio

import httpx

from app.main import app
from app.providers import ProviderError


def request(method, path, **kwargs):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_health_endpoint():
    response = request("GET", "/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "COOKED"}


def test_homepage_serves_the_web_interface():
    response = request("GET", "/")
    assert response.status_code == 200
    assert "COOKED" in response.text
    assert 'id="go"' in response.text
    assert 'id="language"' not in response.text
    for style in ("instagram", "dry", "desi", "absurd"):
        assert f'<option value="{style}">' in response.text


def test_roast_rejects_private_contact_details():
    response = request(
        "POST",
        "/api/roast",
        json={"text": "Reply to person@example.com"},
    )
    assert response.status_code == 400
    assert "Remove phone numbers or email addresses" in response.json()["detail"]


def test_roast_rejects_legacy_language_field():
    response = request(
        "POST",
        "/api/roast",
        json={"text": "A sufficiently long harmless context", "language": "ur"},
    )
    assert response.status_code == 422


def test_roast_returns_structured_result(monkeypatch):
    async def fake_generate(prompt, context, style="instagram", intensity=3):
        assert context == "A harmless test situation."
        assert style == "instagram"
        assert intensity == 3
        return "The situation brought its own plot twist."

    monkeypatch.setattr("app.main.generate", fake_generate)
    response = request(
        "POST",
        "/api/roast",
        json={"text": "A harmless test situation."},
    )
    assert response.status_code == 200
    assert response.json() == {
        "roast": "The situation brought its own plot twist.",
        "style": "instagram",
    }


def test_roast_maps_provider_errors_to_service_unavailable(monkeypatch):
    async def fake_generate(prompt, context, style="instagram", intensity=3):
        raise ProviderError("The model provider timed out. Try again.")

    monkeypatch.setattr("app.main.generate", fake_generate)
    response = request(
        "POST",
        "/api/roast",
        json={"text": "A harmless test situation."},
    )
    assert response.status_code == 503
    assert "timed out" in response.json()["detail"]
