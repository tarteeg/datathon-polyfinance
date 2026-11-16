from datetime import date
from math import isclose
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Asset = Literal["SPY", "TLT"]
Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Status = Literal["within", "at", "beyond"]


class LabRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    weights: dict[Asset, Percent]
    asset: Asset
    shock_pct: float = Field(ge=-100, le=0)
    loss_limit_pct: float = Field(gt=0, le=100)
    principal: float = Field(default=10_000, gt=0, le=1e12)
    currency: Literal["USD"] = "USD"
    start: date = date(2022, 1, 1)
    end: date = date(2022, 12, 31)
    persona: Literal["Robert", "Amira", "Mateo"] = "Robert"

    @model_validator(mode="after")
    def validate_portfolio(self):
        if set(self.weights) != {"SPY", "TLT"} or not isclose(sum(self.weights.values()), 100, rel_tol=0, abs_tol=1e-9):
            raise ValueError("SPY and TLT allocations must total 100%.")
        if not date(2003, 1, 1) <= self.start <= self.end < date.today():
            raise ValueError("Choose a completed historical period starting in 2003 or later.")
        if (self.end - self.start).days > 366 * 5:
            raise ValueError("Select a replay of five years or less.")
        return self


class Scenario(BaseModel):
    impact_pct: float
    impact_usd: float
    limit_usd: float
    threshold_shock_pct: float | None
    can_exceed: bool
    status: Status


class ValuePoint(BaseModel):
    date: str
    usd: float


class Replay(BaseModel):
    total_return_pct: float
    volatility_pct: float
    max_drawdown_pct: float
    peak: str
    trough: str
    drawdown_status: Status
    contributions_pp: dict[Asset, float]
    correlation: float | None
    series: list[ValuePoint]
    retrieved: dict[Asset, str]
    sources: dict[Asset, str]
    trading_days: int
    baseline: str
    last_close: str


class LabResult(BaseModel):
    scenario: Scenario
    replay: Replay | None
    replay_error: str | None
