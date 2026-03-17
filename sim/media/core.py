from __future__ import annotations

from dataclasses import dataclass, field
import uuid


@dataclass(slots=True)
class MediaOutlet:
    outlet_id: str
    name: str
    nation_alignment: str
    ideological_slant: str
    state_controlled: bool
    credibility: float
    reach: float
    censorship_exposure: float
    sensationalism: float


@dataclass(slots=True)
class NewspaperIssue:
    issue_id: str
    outlet_id: str
    publication_tick: int
    region_scope: str
    event_id: str
    headlines: list[str]
    top_stories: list[dict]
    confidence_notes: list[str]
    ideological_framing_tags: list[str]
    narrative_variants: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class MediaSystem:
    outlets: dict[str, MediaOutlet] = field(default_factory=dict)
    issues: list[NewspaperIssue] = field(default_factory=list)
    issue_interval: int = 5

    def ensure_default_outlets(self, nations: list[dict]) -> None:
        if self.outlets:
            return
        self.outlets["outlet-world"] = MediaOutlet(
            outlet_id="outlet-world",
            name="Global Dispatch",
            nation_alignment="global",
            ideological_slant="centrist",
            state_controlled=False,
            credibility=0.72,
            reach=0.9,
            censorship_exposure=0.12,
            sensationalism=0.25,
        )
        for n in nations[:6]:
            nid = n["id"]
            self.outlets[f"outlet-{nid}"] = MediaOutlet(
                outlet_id=f"outlet-{nid}",
                name=f"{n.get('name', nid)} Herald",
                nation_alignment=nid,
                ideological_slant="mixed" if n.get("stability", 0.5) > 0.55 else "polarized",
                state_controlled=n.get("stability", 0.5) < 0.45,
                credibility=0.55,
                reach=0.62,
                censorship_exposure=0.4 if n.get("stability", 0.5) < 0.45 else 0.2,
                sensationalism=0.45,
            )

    def _frame(self, event: dict, outlet: MediaOutlet) -> str:
        base = event.get("message", "Developing situation")
        if outlet.state_controlled:
            return f"Official sources emphasize control: {base}"
        if outlet.ideological_slant in {"polarized", "state"}:
            return f"Power struggle highlighted: {base}"
        if outlet.sensationalism > 0.5:
            return f"BREAKING: {base}"
        if outlet.nation_alignment == "global":
            return f"Regional desks report: {base}"
        return base

    def _confidence(self, outlet: MediaOutlet) -> float:
        return max(0.2, min(0.95, 0.5 * outlet.credibility + 0.3 * (1 - outlet.censorship_exposure) + 0.2 * (1 - outlet.sensationalism)))

    def _bias(self, outlet: MediaOutlet) -> str:
        if outlet.state_controlled:
            return "pro-government"
        if outlet.nation_alignment == "global":
            return "external"
        if outlet.ideological_slant == "polarized":
            return "partisan"
        return "independent"

    def _anchor_events(self, visible_events: list[dict]) -> list[dict]:
        major = [e for e in visible_events[-20:] if e.get("type") in {"security_incident", "coup_risk", "migration", "org_founded", "org_dissolved", "milestone"}]
        return (major or visible_events[-5:])[:3]

    def generate_issue(self, *, tick: int, outlet: MediaOutlet, event: dict, trigger: str) -> NewspaperIssue:
        framed = self._frame(event, outlet)
        confidence = self._confidence(outlet)
        bias = self._bias(outlet)
        headline = f"[{event.get('type', 'update').upper()}] {framed[:84]}"
        issue = NewspaperIssue(
            issue_id=f"issue-{uuid.uuid4().hex[:10]}",
            outlet_id=outlet.outlet_id,
            publication_tick=tick,
            region_scope=outlet.nation_alignment,
            event_id=event.get("id", f"evt-{tick}-{event.get('type','update')}") ,
            headlines=[headline],
            top_stories=[{
                "event_id": event.get("id", ""),
                "event_type": event.get("type", "update"),
                "story": framed,
                "bias": bias,
                "confidence": round(confidence, 2),
                "source_confidence": "medium" if confidence < 0.7 else "high",
            }],
            confidence_notes=["Based on public reports and media-accessible disclosures.", "Interpretation varies by access, censorship, and ideological framing."],
            ideological_framing_tags=[outlet.ideological_slant, "state-controlled" if outlet.state_controlled else "independent", bias],
            narrative_variants=[{
                "outlet": outlet.name,
                "headline": headline,
                "bias": bias,
                "confidence": round(confidence, 2),
            }],
        )
        self.issues.append(issue)
        return issue

    def tick(self, *, tick: int, visible_events: list[dict], nations: list[dict], force_trigger: bool = False) -> list[NewspaperIssue]:
        self.ensure_default_outlets(nations)
        major = any(ev.get("type") in {"coup_risk", "security_incident", "org_founded", "org_dissolved", "migration", "milestone"} for ev in visible_events[-20:])
        if not force_trigger and tick % self.issue_interval != 0 and not major:
            return []
        out: list[NewspaperIssue] = []
        trigger = "major_event" if major else "periodic"
        anchors = self._anchor_events(visible_events)
        if not anchors:
            anchors = [{"id": f"brief-{tick}", "type": "briefing", "message": "No major public events reported."}]

        for anchor in anchors:
            variants: list[dict] = []
            produced: list[NewspaperIssue] = []
            for outlet in self.outlets.values():
                issue = self.generate_issue(tick=tick, outlet=outlet, event=anchor, trigger=trigger)
                variants.extend(issue.narrative_variants)
                produced.append(issue)
            for issue in produced:
                issue.narrative_variants = variants
            out.extend(produced)
        return out
