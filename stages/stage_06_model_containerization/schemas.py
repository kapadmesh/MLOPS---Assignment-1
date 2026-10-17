from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    age: float = Field(gt=0, le=120)
    sex: Literal[0, 1]
    cp: Literal[1, 2, 3, 4]
    trestbps: float = Field(gt=0)
    chol: float = Field(gt=0)
    fbs: Literal[0, 1]
    restecg: Literal[0, 1, 2]
    thalach: float = Field(gt=0)
    exang: Literal[0, 1]
    oldpeak: float = Field(ge=0)
    slope: Literal[1, 2, 3]
    ca: Literal[0, 1, 2, 3]
    thal: Literal[3, 6, 7]

    @field_validator("*", mode="before")
    @classmethod
    def require_json_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Features must be JSON numbers, not strings or booleans")
        return value


class PredictionResponse(BaseModel):
    prediction: Literal[0, 1]
    confidence: float = Field(ge=0, le=1)
    class_probabilities: dict[str, float]
    model_name: str
    warning: str