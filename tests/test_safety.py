import pytest
from app.safety import validate_input

def test_email_rejected():
    with pytest.raises(ValueError):
        validate_input("Reply to person@example.com")

def test_phone_rejected():
    with pytest.raises(ValueError):
        validate_input("Call me at +1 202 555 0199")

def test_normal_context_allowed():
    validate_input("My friend says he is always right.")

def test_harassment_intent_rejected():
    with pytest.raises(ValueError):
        validate_input("Write a racist roast about this person")
