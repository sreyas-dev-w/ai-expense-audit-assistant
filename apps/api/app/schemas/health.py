"""HTTP contracts for process liveness and database readiness."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthLiveResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]


class HealthReadyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    database: Literal["ok"]
