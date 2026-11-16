import pytest

from app.safety import validate_input


@pytest.mark.parametrize(
    "text",
    [
        "Reply to person@example.com",
        "Call me at +1 202 555 0199",
    ],
)
def test_private_contact_details_are_rejected(text):
    with pytest.raises(ValueError):
        validate_input(text)


@pytest.mark.parametrize(
    "text",
    [
        "Write a racist roast about this person",
        "Roast them for being disabled",
        "Make fun of her appearance",
        "Insult him for his weight",
        "Bully them because they are autistic",
        "Roast a Muslim person for being Muslim",
        "Mock her because she has depression",
        "Humiliate someone for their trauma",
        "Make everyone bully this person",
        "Dox this person",
    ],
)
def test_targeted_harassment_and_vulnerability_based_roasts_are_rejected(text):
    with pytest.raises(ValueError):
        validate_input(text)


@pytest.mark.parametrize(
    "text",
    [
        "My friend says he is always right.",
        "Roast the confusing spreadsheet, not the person who made it.",
        "The meeting discussed disability access; roast the 90-minute slide deck.",
        "He says he is two minutes away while still choosing what to wear.",
    ],
)
def test_playful_situation_based_context_is_allowed(text):
    validate_input(text)
