# Bend Interface Contracts (Phase 5 Prep)

This document defines **candidate heavy-kernel boundaries** for incremental Bend migration.
Python remains orchestration/control plane.

## Candidate kernel 1: score_agents(batch)
Input:
- contiguous arrays of needs/perception/trait features
- deterministic seed stream offsets
Output:
- action utility matrix per agent
- optional top-k action ids

## Candidate kernel 2: migration_score(batch)
Input:
- agent-city feature matrix
- city pressure vectors
Output:
- migration score vectors
- selected target indices

## Candidate kernel 3: propagate_influence(graph, signals)
Input:
- compressed adjacency lists
- node signal vectors
Output:
- updated influence vectors

## Candidate kernel 4: conflict_score(batch)
Input:
- legitimacy/intelligence/urban pressure vectors
Output:
- incident risk vectors

## Candidate kernel 5: org_influence_aggregate(members, stabilities)
Input:
- member ids + stability weights
Output:
- normalized influence map + bloc candidates

## Candidate kernel 6: aggregate_metrics(values)
Input:
- partial metric vectors
Output:
- deterministic reduced metrics

---

## Data layout expectations
- Prefer structure-of-arrays (SoA) for dense numeric kernels.
- Stable deterministic ordering by entity id index maps.
- Explicit seed offset contract passed from Python scheduler.

## What remains in Python
- service integration and retries
- model calls and degraded fallbacks
- scenario/tuning application
- persistence/snapshot/replay management
- operator API/frontend workflows
