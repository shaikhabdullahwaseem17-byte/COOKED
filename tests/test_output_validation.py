import pytest

from app.output_validation import is_valid_output


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        ("That apology needs its own apology.", "en", True),
        ("یہ فیصلہ خود بھی مشورہ مانگتا ہے۔", "ur", True),
        ("Yeh faisla khud bhi mashwara maangta hai.", "ur-rom", True),
        ("यह मीटिंग कभी खत्म नहीं होगी।", "hi", True),
        ("ریس کرتے ہوئے ناقص تلاش", "ur-rom", False),
        ("یہ ایک بے ربط English mix ہے", "ur", False),
        ("यह is mixed script", "hi", False),
        ("", "en", False),
        ("123 !!!", "en", False),
    ],
)
def test_output_script_validation(text, language, expected):
    assert is_valid_output(text, language) is expected
