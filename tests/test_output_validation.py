import pytest

from app.output_validation import is_valid_output


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("That apology needs its own apology.", True),
        ("یہ فیصلہ خود بھی مشورہ مانگتا ہے۔", False),
        ("यह मीटिंग कभी खत्म नहीं होगी।", False),
        ("", False),
        ("123 !!!", False),
        ("This is English with a stray क character.", False),
        ("A normal English comeback.", True),
    ],
)
def test_english_output_validation(text, expected):
    assert is_valid_output(text) is expected
