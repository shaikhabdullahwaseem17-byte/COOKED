from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Style = Literal["instagram", "dry", "desi", "absurd"]

class RoastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=3, max_length=600)
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
    style: Style
