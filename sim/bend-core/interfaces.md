# Bend Interface Contracts

## score_agents(batch)
Input: contiguous arrays of needs/perception features.
Output: action utility matrix.

## propagate_influence(graph, signals)
Input: adjacency + scalar/vector signals.
Output: updated influence signals.

## clear_market(offers, bids)
Input: batched supply/demand book.
Output: clearing prices and allocation vectors.

## regional_update(regions)
Input: region state vectors.
Output: next-step region vectors.

## aggregate_metrics(values)
Input: distributed partial metrics.
Output: deterministic reduced metrics.
