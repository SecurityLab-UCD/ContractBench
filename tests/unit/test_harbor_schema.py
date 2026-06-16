"""Unit tests for Harbor reward.json schema validation and conversion."""

from __future__ import annotations

import pytest

from benchmark.core.failure_labels import FailureLabel
from benchmark.evaluation.harbor_schema import (
    TASK_CATALOG,
    VALID_TASK_IDS,
    harbor_reward_to_episode,
    primary_failure_label,
    validate_harbor_reward,
)
from benchmark.evaluation.schema import validate_episode_dict


# ── validate_harbor_reward ──────────────────────────────────────────────


class TestValidateHarborReward:
    # Note: as of PR #13, validate_harbor_reward returns (errors, warnings).
    # Structural problems produce errors; non-canonical labels produce
    # warnings in default mode, or errors in strict mode.

    def test_valid_success(self):
        data = {
            "reward": 1.0,
            "task_id": "presigned-url-download",
            "suite": "both",
            "success": True,
            "failure_labels": [],
            "server_log_summary": {"SUCCESS": 1},
        }
        assert validate_harbor_reward(data) == ([], [])

    def test_valid_failure(self):
        data = {
            "reward": 0.0,
            "task_id": "csrf-form-submit",
            "suite": "integrity",
            "success": False,
            "failure_labels": [
                {"label": "MUTATED_TOKEN", "detail": "mismatch"},
            ],
            "server_log_summary": {"MUTATED_TOKEN": 1},
        }
        assert validate_harbor_reward(data) == ([], [])

    def test_missing_required_field(self):
        data = {"reward": 1.0, "task_id": "x", "suite": "validity"}
        errors, _ = validate_harbor_reward(data)
        assert any("success" in e for e in errors)

    def test_invalid_reward_range(self):
        data = {
            "reward": 1.5,
            "task_id": "x",
            "suite": "validity",
            "success": True,
        }
        errors, _ = validate_harbor_reward(data)
        assert any("reward" in e for e in errors)

    def test_invalid_suite(self):
        data = {
            "reward": 0.0,
            "task_id": "x",
            "suite": "patience",
            "success": False,
        }
        errors, _ = validate_harbor_reward(data)
        assert any("suite" in e for e in errors)

    def test_suite_both_is_valid(self):
        data = {
            "reward": 0.5,
            "task_id": "multi-token-workflow",
            "suite": "both",
            "success": False,
        }
        assert validate_harbor_reward(data) == ([], [])

    def test_invalid_failure_label_is_warning_by_default(self):
        data = {
            "reward": 0.0,
            "task_id": "x",
            "suite": "validity",
            "success": False,
            "failure_labels": [{"label": "NOT_A_REAL_LABEL"}],
        }
        errors, warnings = validate_harbor_reward(data)
        # Default: non-canonical label does not invalidate the episode.
        assert not any("NOT_A_REAL_LABEL" in e for e in errors)
        assert any("NOT_A_REAL_LABEL" in w for w in warnings)

    def test_invalid_failure_label_is_error_in_strict_mode(self):
        data = {
            "reward": 0.0,
            "task_id": "x",
            "suite": "validity",
            "success": False,
            "failure_labels": [{"label": "NOT_A_REAL_LABEL"}],
        }
        errors, _ = validate_harbor_reward(data, strict=True)
        assert any("NOT_A_REAL_LABEL" in e for e in errors)

    def test_invalid_server_log_summary_key_is_warning_by_default(self):
        data = {
            "reward": 0.0,
            "task_id": "x",
            "suite": "validity",
            "success": False,
            "server_log_summary": {"FAKE_LABEL": 1},
        }
        errors, warnings = validate_harbor_reward(data)
        assert not any("FAKE_LABEL" in e for e in errors)
        assert any("FAKE_LABEL" in w for w in warnings)

    def test_invalid_server_log_summary_key_is_error_in_strict_mode(self):
        data = {
            "reward": 0.0,
            "task_id": "x",
            "suite": "validity",
            "success": False,
            "server_log_summary": {"FAKE_LABEL": 1},
        }
        errors, _ = validate_harbor_reward(data, strict=True)
        assert any("FAKE_LABEL" in e for e in errors)


# ── primary_failure_label ───────────────────────────────────────────────


class TestPrimaryFailureLabel:
    def test_success(self):
        data = {"success": True, "server_log_summary": {"SUCCESS": 3}}
        assert primary_failure_label(data) == "SUCCESS"

    def test_single_failure(self):
        data = {
            "success": False,
            "server_log_summary": {"EXPIRED_BEFORE_USE": 1},
        }
        assert primary_failure_label(data) == "EXPIRED_BEFORE_USE"

    def test_most_common_failure(self):
        data = {
            "success": False,
            "server_log_summary": {
                "SUCCESS": 2,
                "EXPIRED_BEFORE_USE": 3,
                "RATE_LIMITED": 1,
            },
        }
        assert primary_failure_label(data) == "EXPIRED_BEFORE_USE"

    def test_fallback_to_failure_labels_list(self):
        data = {
            "success": False,
            "failure_labels": [{"label": "TRUNCATED"}],
        }
        assert primary_failure_label(data) == "TRUNCATED"

    def test_fallback_to_other(self):
        data = {"success": False}
        assert primary_failure_label(data) == "OTHER"


# ── harbor_reward_to_episode ────────────────────────────────────────────


class TestHarborRewardToEpisode:
    def test_basic_conversion(self):
        data = {
            "reward": 1.0,
            "task_id": "presigned-url-download",
            "suite": "both",
            "success": True,
            "failure_labels": [],
            "server_log_summary": {"SUCCESS": 1},
        }
        ep = harbor_reward_to_episode(data, agent="test-agent", run_id=3)
        assert ep["task_id"] == "presigned-url-download"
        assert ep["suite"] == "both"
        assert ep["agent"] == "test-agent"
        assert ep["seed"] == 3
        assert ep["success"] is True
        assert ep["failure_label"] == "SUCCESS"
        assert ep["reward"] == 1.0

    def test_failure_conversion(self):
        data = {
            "reward": 0.0,
            "task_id": "csrf-form-submit",
            "suite": "integrity",
            "success": False,
            "failure_labels": [{"label": "MUTATED_TOKEN", "detail": "mismatch"}],
            "server_log_summary": {"MUTATED_TOKEN": 1},
        }
        ep = harbor_reward_to_episode(data, agent="gpt-4o", run_id=0)
        assert ep["failure_label"] == "MUTATED_TOKEN"
        assert ep["success"] is False
        assert ep["difficulty"] == "hard"

    def test_catalog_override_suite(self):
        """Suite from catalog takes precedence over reward.json value."""
        data = {
            "reward": 0.5,
            "task_id": "multi-token-workflow",
            "suite": "integrity",  # Wrong in reward.json
            "success": False,
        }
        ep = harbor_reward_to_episode(data, agent="test", run_id=0)
        assert ep["suite"] == "both"  # Corrected from catalog

    def test_episode_passes_schema_validation(self):
        """Converted episodes must pass the EpisodeResult schema validator."""
        data = {
            "reward": 1.0,
            "task_id": "presigned-url-download",
            "suite": "both",
            "success": True,
            "failure_labels": [],
            "server_log_summary": {"SUCCESS": 1},
        }
        ep = harbor_reward_to_episode(data, agent="test", run_id=0)
        errors = validate_episode_dict(ep)
        assert errors == [], f"Schema errors: {errors}"


# ── TASK_CATALOG ────────────────────────────────────────────────────────


class TestTaskCatalog:
    def test_has_33_tasks(self):
        assert len(TASK_CATALOG) == 33

    def test_all_tasks_have_required_fields(self):
        for task_id, meta in TASK_CATALOG.items():
            assert "suite" in meta, f"{task_id} missing suite"
            assert "difficulty" in meta, f"{task_id} missing difficulty"
            assert "category" in meta, f"{task_id} missing category"

    def test_suite_distribution(self):
        suites = [m["suite"] for m in TASK_CATALOG.values()]
        assert suites.count("validity") == 0
        assert suites.count("integrity") == 0
        assert suites.count("both") == 33

    def test_difficulty_distribution(self):
        diffs = [m["difficulty"] for m in TASK_CATALOG.values()]
        assert "medium" in diffs
        assert "hard" in diffs
