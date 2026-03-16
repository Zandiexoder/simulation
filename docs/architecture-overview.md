# Architecture Overview

## Phase-3 Additions

- Migration system with scored, non-random relocation decisions.
- Urban dynamics model for growth/decline and capacity pressure.
- Politics/governance model with legitimacy, protests, and coup-risk.
- Intelligence + counterintelligence report model and fog-of-war views.
- Conflict/security model with uncertainty-driven incidents.
- History/timeline replay support via event windows + indexed snapshots.

## Mutation Boundary

`API -> Scheduler -> Kernel` remains the only mutation path for world state.

## Epistemic Separation

Every in-world decision layer uses separated knowledge domains:
- true
- observed
- reported
- inferred
- believed
- unknown

Frontend inspector defaults to non-omniscient readouts.

## Replay Design

History stores:
- timestamped events
- periodic snapshots
- tick-compare deltas
- replay windows for timeline browsing
