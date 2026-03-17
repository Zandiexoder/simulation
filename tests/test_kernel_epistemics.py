from dataclasses import asdict
from sim.kernel.pipeline import SimulationKernel
from sim.kernel.state import SimulationState
from sim.worldgen.generator import generate_world, seed_nations, seed_settlements


def test_epistemic_limits_have_unknown_bucket():
    state = SimulationState(seed=9)
    world = generate_world(seed=9, width=12, height=8)
    state.world_map = {"width": world.width, "height": world.height, "cells": [asdict(c) for c in world.cells]}
    state.cities = seed_settlements(world, n_cities=2)
    state.nations = seed_nations(2)
    state.agents = [{"id": "agent-1", "name": "A", "tier": 1, "city_id": state.cities[0]['id']}]
    state.ecs.location['agent-1'] = (state.cities[0]['x'], state.cities[0]['y'])
    state.ecs.needs['agent-1'] = {'hunger': 0.5, 'wealth': 0.5}
    kernel = SimulationKernel(state)
    kernel.step(1)
    ks = state.knowledge_state['agent-1']
    assert 'unknown' in ks
    assert 'other_agents_private_goals' in ks['unknown']
