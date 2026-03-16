from sim.kernel.pipeline import SimulationKernel
from sim.kernel.state import SimulationState
from sim.scheduler import Scheduler


def test_scheduler_tick_control_and_speed():
    state = SimulationState(seed=3)
    state.agents = []
    kernel = SimulationKernel(state)
    scheduler = Scheduler(kernel=kernel, state=state, speed=2, snapshot_interval=2)
    scheduler.start()
    scheduler.step(1)
    assert state.tick == 2
    scheduler.set_speed(3)
    scheduler.step(2)
    assert state.tick == 8
    scheduler.pause()
    assert state.running is False
