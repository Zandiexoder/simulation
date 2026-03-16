from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Literal


class Intervention(BaseModel):
    type: str
    target: str
    rationale: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GMResponse(BaseModel):
    message: str
    perspective: Literal["public", "actor", "intel", "admin"] = "public"
    uncertainty_notes: list[str] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)


class IntelligenceReport(BaseModel):
    report_id: str
    source_type: str
    source_reliability: float
    timestamp_tick: int
    staleness: float
    target_scope: str
    confidence_score: float
    possible_bias: str
    secrecy_level: Literal["public", "restricted", "secret", "top_secret"]
    assessed_truth_likelihood: float
    report_summary: str
    structured_claims: dict[str, Any] = Field(default_factory=dict)
