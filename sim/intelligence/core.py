from __future__ import annotations

from dataclasses import dataclass, field
import uuid


@dataclass(slots=True)
class IntelReport:
    report_id: str
    source_type: str
    source_reliability: float
    timestamp_tick: int
    staleness: float
    target_scope: str
    confidence_score: float
    possible_bias: str
    secrecy_level: str
    assessed_truth_likelihood: float
    report_summary: str
    structured_claims: dict


@dataclass(slots=True)
class IntelligenceSystem:
    reports: list[IntelReport] = field(default_factory=list)
    nation_fog: dict[str, dict] = field(default_factory=dict)

    def add_report(self, *, tick: int, target_scope: str, source_type: str = "informant", reliability: float = 0.6, confidence: float = 0.55,
                   bias: str = "unknown", secrecy: str = "secret", summary: str = "") -> IntelReport:
        report = IntelReport(
            report_id=str(uuid.uuid4()),
            source_type=source_type,
            source_reliability=reliability,
            timestamp_tick=tick,
            staleness=0.0,
            target_scope=target_scope,
            confidence_score=confidence,
            possible_bias=bias,
            secrecy_level=secrecy,
            assessed_truth_likelihood=max(0.0, min(1.0, reliability * 0.6 + confidence * 0.4)),
            report_summary=summary or f"Assessment on {target_scope}",
            structured_claims={"status": "partial", "target_scope": target_scope},
        )
        self.reports.append(report)
        return report

    def tick(self, tick: int) -> None:
        for r in self.reports:
            r.staleness = min(1.0, max(0.0, (tick - r.timestamp_tick) / 50))

    def update_fog(self, nation_id: str, known: dict, suspected: dict, estimated: dict, unknown: list[str]) -> None:
        self.nation_fog[nation_id] = {
            "known": known,
            "suspected": suspected,
            "estimated": estimated,
            "unknown": unknown,
        }
