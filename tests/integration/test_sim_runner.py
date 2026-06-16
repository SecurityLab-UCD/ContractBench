from __future__ import annotations

from benchmark.generators.contractbench import make_validity_suite
from benchmark.runner.sim_runner import BaselineAgent, ValidityAwareAgent, run_suite


def test_validity_suite_shows_temporal_gap():
    tasks = make_validity_suite(seed=0)
    agents = [BaselineAgent(), ValidityAwareAgent()]

    static_results = run_suite(task_configs=tasks, agents=agents, static_mode=True)
    temporal_results = run_suite(task_configs=tasks, agents=agents, static_mode=False)

    static_by_agent = {a.name: [r for r in static_results if r.agent == a.name] for a in agents}
    temporal_by_agent = {a.name: [r for r in temporal_results if r.agent == a.name] for a in agents}

    assert all(r.success for r in static_by_agent["naive"])
    assert all(r.success for r in static_by_agent["validity_aware"])

    naive_temporal_success = sum(r.success for r in temporal_by_agent["naive"])
    aware_temporal_success = sum(r.success for r in temporal_by_agent["validity_aware"])
    assert aware_temporal_success >= naive_temporal_success
