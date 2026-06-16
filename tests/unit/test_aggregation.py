"""Unit tests for the Harbor results aggregation pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from benchmark.evaluation.harbor_schema import (
    harbor_reward_to_episode,
    validate_harbor_reward,
)

# Import aggregation functions — they live in the script but we import from
# the module path after path setup.
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "experiments" / "scripts"))

from aggregate_harbor_results import (
    compute_metrics,
    find_reward_files,
    infer_agent_and_run,
    parse_all_results,
    write_latex_table,
    write_macros,
    write_results_json,
)

FIXTURES_DIR = _ROOT / "tests" / "fixtures" / "harbor_results"


# ── find_reward_files ───────────────────────────────────────────────────


class TestFindRewardFiles:
    def test_finds_fixture_files(self):
        files = find_reward_files(FIXTURES_DIR)
        assert len(files) >= 10  # We created 12 fixtures

    def test_all_are_json(self):
        files = find_reward_files(FIXTURES_DIR)
        for f in files:
            assert f.name == "reward.json"

    def test_returns_empty_for_nonexistent_dir(self):
        files = find_reward_files(Path("/nonexistent/path"))
        assert files == []


# ── infer_agent_and_run ─────────────────────────────────────────────────


class TestInferAgentAndRun:
    def test_standard_layout(self):
        p = FIXTURES_DIR / "agent_a" / "run_0" / "presigned-url-download" / "reward.json"
        agent, run_id = infer_agent_and_run(p, FIXTURES_DIR)
        assert agent == "agent_a"
        assert run_id == 0

    def test_run_1(self):
        p = FIXTURES_DIR / "agent_a" / "run_1" / "csrf-form-submit" / "reward.json"
        agent, run_id = infer_agent_and_run(p, FIXTURES_DIR)
        assert agent == "agent_a"
        assert run_id == 1

    def test_different_agent(self):
        p = FIXTURES_DIR / "agent_b" / "run_0" / "presigned-url-download" / "reward.json"
        agent, run_id = infer_agent_and_run(p, FIXTURES_DIR)
        assert agent == "agent_b"
        assert run_id == 0


# ── parse_all_results ───────────────────────────────────────────────────


class TestParseAllResults:
    def test_parses_all_fixtures(self):
        episodes = parse_all_results(FIXTURES_DIR)
        assert len(episodes) >= 10

    def test_episodes_have_required_fields(self):
        episodes = parse_all_results(FIXTURES_DIR)
        required = {"task_id", "suite", "seed", "agent", "success", "failure_label"}
        for ep in episodes:
            missing = required - set(ep.keys())
            assert not missing, f"Episode missing fields: {missing}"

    def test_agents_are_correct(self):
        episodes = parse_all_results(FIXTURES_DIR)
        agents = {ep["agent"] for ep in episodes}
        assert "agent_a" in agents
        assert "agent_b" in agents

    def test_skips_invalid_json(self):
        """Parser should skip malformed JSON files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_dir = Path(tmpdir) / "bad_agent" / "run_0" / "task"
            bad_dir.mkdir(parents=True)
            (bad_dir / "reward.json").write_text("{invalid json")
            episodes = parse_all_results(Path(tmpdir))
            assert episodes == []


# ── compute_metrics ─────────────────────────────────────────────────────


class TestComputeMetrics:
    @pytest.fixture
    def episodes(self):
        return parse_all_results(FIXTURES_DIR)

    def test_overall_metrics(self, episodes):
        m = compute_metrics(episodes, n_bootstrap=1000, bootstrap_seed=42)
        overall = m["overall"]
        assert 0.0 <= overall["success_rate"] <= 1.0
        assert overall["ci_lower"] <= overall["success_rate"] <= overall["ci_upper"]
        assert overall["n"] == len(episodes)

    def test_by_agent(self, episodes):
        m = compute_metrics(episodes, n_bootstrap=1000, bootstrap_seed=42)
        assert "agent_a" in m["by_agent"]
        assert "agent_b" in m["by_agent"]

    def test_by_task(self, episodes):
        m = compute_metrics(episodes, n_bootstrap=1000, bootstrap_seed=42)
        assert "presigned-url-download" in m["by_task"]

    def test_by_suite(self, episodes):
        m = compute_metrics(episodes, n_bootstrap=1000, bootstrap_seed=42)
        # All tasks are now "both" suite
        assert "both" in m["by_suite"]

    def test_failure_distribution(self, episodes):
        m = compute_metrics(episodes, n_bootstrap=1000, bootstrap_seed=42)
        fd = m["failure_distribution"]
        # Our fixtures include EXPIRED_BEFORE_USE, MUTATED_TOKEN, TRUNCATED
        assert isinstance(fd, dict)
        # At least some failures exist
        assert sum(fd.values()) > 0

    def test_deterministic(self, episodes):
        m1 = compute_metrics(episodes, n_bootstrap=1000, bootstrap_seed=42)
        m2 = compute_metrics(episodes, n_bootstrap=1000, bootstrap_seed=42)
        assert m1["overall"]["success_rate"] == m2["overall"]["success_rate"]
        assert m1["overall"]["ci_lower"] == m2["overall"]["ci_lower"]

    def test_empty_episodes(self):
        m = compute_metrics([], n_bootstrap=100, bootstrap_seed=42)
        assert m["overall"]["success_rate"] == 0.0
        assert m["overall"]["n"] == 0


# ── Output writers ──────────────────────────────────────────────────────


class TestOutputWriters:
    @pytest.fixture
    def episodes_and_metrics(self):
        episodes = parse_all_results(FIXTURES_DIR)
        metrics = compute_metrics(episodes, n_bootstrap=100, bootstrap_seed=42)
        return episodes, metrics

    def test_write_results_json(self, episodes_and_metrics, tmp_path):
        episodes, metrics = episodes_and_metrics
        out = tmp_path / "results.json"
        write_results_json(episodes, metrics, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert "episodes" in data
        assert "metrics" in data
        assert data["n_episodes"] == len(episodes)

    def test_write_latex_table(self, episodes_and_metrics, tmp_path):
        _, metrics = episodes_and_metrics
        out = tmp_path / "table.tex"
        write_latex_table(metrics, out)
        assert out.exists()
        content = out.read_text()
        assert "\\begin{table}" in content
        assert "\\end{table}" in content
        assert "agent" in content.lower()

    def test_write_macros(self, episodes_and_metrics, tmp_path):
        _, metrics = episodes_and_metrics
        out = tmp_path / "macros.tex"
        write_macros(metrics, out)
        assert out.exists()
        content = out.read_text()
        assert "\\newcommand" in content
        assert "SuccessRateOverall" in content
        assert "NumHarborTasks" in content
