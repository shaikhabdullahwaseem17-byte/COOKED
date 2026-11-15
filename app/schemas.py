from typing import Literal
from pydantic import BaseModel, Field, field_validator

Language = Literal["en", "ur", "ur-rom", "hi"]
Style = Literal["instagram", "dry", "desi", "absurd"]

class RoastRequest(BaseModel):
    text: str = Field(min_length=3, max_length=600)
    language: Language = "en"
    style: Style = "instagram"
    intensity: int = Field(default=3, ge=1, le=5)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Give COOKED a little more context.")
        return value

class RoastResponse(BaseModel):
    roast: str
    language: Language
    style: Style
