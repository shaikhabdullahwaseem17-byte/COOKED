import pytest

from app.output_validation import is_valid_output


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        ("That apology needs its own apology.", "en", True),
        ("یہ فیصلہ خود بھی مشورہ مانگتا ہے۔", "en", False),
        ("यह मीटिंग कभी खत्म नहीं होगी।", "en", False),
        ("", "en", False),
        ("123 !!!", "en", False),
        ("This is English with a stray क character.", "en", False),
        ("A normal English comeback.", "ur", False),
    ],
)
def test_english_output_validation(text, language, expected):
    assert is_valid_output(text, language) is expected
