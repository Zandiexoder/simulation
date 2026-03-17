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
    summary: str = ""
    historical_analogies: list[dict[str, Any]] = Field(default_factory=list)
    risk_assessment: list[dict[str, Any]] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    possible_trajectories: list[dict[str, Any]] = Field(default_factory=list)
    causal_summary: str = ""
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


class InternationalOrganization(BaseModel):
    org_id: str
    name: str
    org_type: str
    founding_members: list[str]
    members: list[str]
    charter: str
    mandate: list[str]
    legitimacy: float
    enforcement_capacity: float
    budget: float
    voting_structure: str
    membership_rules: str
    ideological_character: str
    prestige: float
    institutional_effectiveness: float


class MediaIssue(BaseModel):
    issue_id: str
    outlet_id: str
    publication_tick: int
    region_scope: str
    headlines: list[str]
    top_stories: list[dict[str, Any]] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    ideological_framing_tags: list[str] = Field(default_factory=list)
