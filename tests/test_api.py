from fastapi.testclient import TestClient

from app.main import app
from app.providers import ProviderError

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "COOKED"}


def test_homepage_serves_the_web_interface():
    response = client.get("/")
    assert response.status_code == 200
    assert "COOKED" in response.text
    assert 'id="go"' in response.text


def test_roast_rejects_private_contact_details():
    response = client.post(
        "/api/roast",
        json={"text": "Reply to person@example.com"},
    )
    assert response.status_code == 400
    assert "Remove phone numbers or email addresses" in response.json()["detail"]


def test_roast_rejects_invalid_language():
    response = client.post(
        "/api/roast",
        json={"text": "A sufficiently long harmless context", "language": "fr"},
    )
    assert response.status_code == 422


def test_roast_returns_structured_result(monkeypatch):
    async def fake_generate(prompt, context, language="en", style="instagram"):
        assert context == "A harmless test situation."
        assert language == "en"
        assert style == "instagram"
        return "The situation brought its own plot twist."

    monkeypatch.setattr("app.main.generate", fake_generate)
    response = client.post(
        "/api/roast",
        json={"text": "A harmless test situation."},
    )
    assert response.status_code == 200
    assert response.json() == {
        "roast": "The situation brought its own plot twist.",
        "language": "en",
        "style": "instagram",
    }


def test_roast_maps_provider_errors_to_service_unavailable(monkeypatch):
    async def fake_generate(prompt, context, language="en", style="instagram"):
        raise ProviderError("The model provider timed out. Try again.")

    monkeypatch.setattr("app.main.generate", fake_generate)
    response = client.post(
        "/api/roast",
        json={"text": "A harmless test situation."},
    )
    assert response.status_code == 503
    assert "timed out" in response.json()["detail"]
