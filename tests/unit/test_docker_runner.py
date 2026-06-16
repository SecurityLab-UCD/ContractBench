"""Tests for the Docker task runner (agents.docker_runner).

These are unit tests that don't require Docker — they test the logic
and data structures, not actual container execution.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.base import AgentResult, BashToolCall, LLMAgent, Message
from agents.docker_runner import HARBOR_TASKS_DIR, TaskRunResult


class MockAgent(LLMAgent):
    """A mock agent that returns predefined responses."""

    provider = "mock"

    def __init__(self, responses=None, **kwargs):
        super().__init__("mock-model", **kwargs)
        self._responses = responses or []
        self._call_count = 0

    def generate(self, messages):
        if self._call_count < len(self._responses):
            r = self._responses[self._call_count]
            self._call_count += 1
            return r
        return AgentResult(text="DONE")


class TestTaskRunResult:
    def test_defaults(self):
        r = TaskRunResult(task_name="test", agent_name="mock", run_id=0)
        assert r.reward == 0.0
        assert r.success is False
        assert r.error is None
        assert r.turns == 0

    def test_success(self):
        r = TaskRunResult(
            task_name="test",
            agent_name="mock",
            run_id=0,
            reward=1.0,
            success=True,
            turns=5,
        )
        assert r.success
        assert r.reward == 1.0


class TestMockAgent:
    def test_returns_done_when_no_responses(self):
        agent = MockAgent()
        r = agent.generate([])
        assert r.is_done
        assert r.text == "DONE"

    def test_returns_tool_calls(self):
        responses = [
            AgentResult(
                text="let me run a command",
                tool_calls=[BashToolCall(call_id="1", command="curl http://localhost:8080/task")],
            ),
            AgentResult(text="DONE"),
        ]
        agent = MockAgent(responses=responses)

        r1 = agent.generate([])
        assert r1.wants_tool_execution
        assert len(r1.tool_calls) == 1
        assert "curl" in r1.tool_calls[0].command

        r2 = agent.generate([])
        assert r2.is_done

    def test_agent_repr(self):
        agent = MockAgent()
        assert "mock-model" in repr(agent)


class TestHarborTasksDir:
    def test_points_to_correct_location(self):
        assert HARBOR_TASKS_DIR.name == "tasks"
        assert HARBOR_TASKS_DIR.parent.name == "harbor"


class TestRunTaskMissingDir:
    def test_returns_error_for_missing_task(self):
        from agents.docker_runner import run_task

        agent = MockAgent()
        result = run_task(
            task_name="nonexistent-task-xyz",
            agent=agent,
            run_id=0,
            quiet=True,
        )
        assert result.error is not None
        assert "not found" in result.error
