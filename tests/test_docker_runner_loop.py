"""Tests for ``agents.docker_runner.run_agent_loop``.

The agent loop is the part of ``run_task`` that handles the conversation
between the LLM and the bash tool executor. It must record **every**
assistant turn — including plain-text responses that have no tool calls —
so the trace is debuggable.

Bug being guarded against:
    When a small model produces a response with no parseable tool calls,
    ``AgentResult.is_done`` is True, and the loop used to ``break`` before
    appending the assistant message. The resulting trace had only the
    system + user messages, with no record of what the model actually
    wrote. This made 100% of Qwen3.5-9B runs look like empty
    "no failure labels" episodes when in fact the model had generated
    hundreds of output tokens.

Run with:
    pytest tests/test_docker_runner_loop.py -v
"""

from __future__ import annotations

from typing import List

import pytest

from agents.base import AgentResult, BashToolCall, LLMAgent, Message
from agents.docker_runner import run_agent_loop


# ---------------------------------------------------------------------------
# Fakes: in-memory agent + tool executor so we can test the loop with no
# Docker, no network, no LLM calls.
# ---------------------------------------------------------------------------


class FakeAgent(LLMAgent):
    """Replays a canned script of ``AgentResult`` objects across calls."""

    provider = "fake"
    model = "fake"

    def __init__(self, scripted_results: List[AgentResult]):
        self._scripted = list(scripted_results)
        self._calls = 0

    def generate(self, messages: List[Message]) -> AgentResult:  # type: ignore[override]
        if self._calls >= len(self._scripted):
            # Default to is_done=True (no tool calls) to stop the loop.
            return AgentResult(text="done", tool_calls=[])
        r = self._scripted[self._calls]
        self._calls += 1
        return r

    @property
    def call_count(self) -> int:
        return self._calls


def fake_tool_executor(tc: BashToolCall) -> str:
    """Deterministic fake that echoes the command."""
    return f"fake-output-for: {tc.command}"


def _initial_messages() -> List[Message]:
    return [
        Message(role="system", content="system prompt"),
        Message(role="user", content="please do the task"),
    ]


# ---------------------------------------------------------------------------
# Bug: plain-text response on turn 1 must still be recorded
# ---------------------------------------------------------------------------


def test_plain_text_first_turn_response_is_recorded_in_messages():
    """Regression test for the Qwen3.5-9B empty-trace bug.

    When an agent returns text but no tool calls on turn 1, the assistant
    message must appear in the conversation history so a human debugger can
    see what the model actually wrote.
    """
    messages = _initial_messages()
    plain_text_result = AgentResult(
        text="I don't know how to do this task.",
        tool_calls=[],
        usage={"input_tokens": 5000, "output_tokens": 160},
    )
    agent = FakeAgent([plain_text_result])

    turns, in_tok, out_tok = run_agent_loop(
        agent=agent,
        messages=messages,
        tool_executor=fake_tool_executor,
        max_turns=30,
    )

    # The loop should have stopped after one call (is_done on turn 1).
    assert turns == 1
    assert in_tok == 5000
    assert out_tok == 160

    # THE BUG: before the fix, messages still had length 2 here. After the
    # fix, the assistant message is appended before the is_done check, so
    # messages has length 3 and we can see what the model wrote.
    assert len(messages) == 3, (
        f"expected assistant message to be recorded, got {len(messages)} "
        f"messages: {[m.role for m in messages]}"
    )
    assistant_msg = messages[2]
    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == "I don't know how to do this task."
    assert assistant_msg.tool_calls == []


# ---------------------------------------------------------------------------
# Regression guards: normal multi-turn behavior still works
# ---------------------------------------------------------------------------


def test_normal_tool_call_flow_records_assistant_and_tool_messages():
    """Agent calls a bash tool, gets output, then finishes."""
    messages = _initial_messages()
    agent = FakeAgent([
        AgentResult(
            text="Let me check the server.",
            tool_calls=[BashToolCall(call_id="c1", command="curl http://localhost:8080/")],
            usage={"input_tokens": 100, "output_tokens": 20},
        ),
        AgentResult(
            text="Done.",
            tool_calls=[],
            usage={"input_tokens": 200, "output_tokens": 5},
        ),
    ])

    turns, in_tok, out_tok = run_agent_loop(
        agent=agent,
        messages=messages,
        tool_executor=fake_tool_executor,
        max_turns=30,
    )

    assert turns == 2
    assert in_tok == 300
    assert out_tok == 25
    # system, user, assistant#1, tool#1, assistant#2
    assert [m.role for m in messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
    ]
    # Tool call is recorded on the first assistant message
    assert messages[2].tool_calls[0].command == "curl http://localhost:8080/"
    # Tool output is the fake executor's echo
    assert messages[3].content == "fake-output-for: curl http://localhost:8080/"


def test_multi_turn_tool_execution_records_all_turns():
    """A 3-turn flow with two tool calls records every assistant message."""
    messages = _initial_messages()
    agent = FakeAgent([
        AgentResult(
            text="first action",
            tool_calls=[BashToolCall(call_id="c1", command="ls")],
            usage={"input_tokens": 10, "output_tokens": 5},
        ),
        AgentResult(
            text="second action",
            tool_calls=[BashToolCall(call_id="c2", command="pwd")],
            usage={"input_tokens": 20, "output_tokens": 5},
        ),
        AgentResult(
            text="finished",
            tool_calls=[],
            usage={"input_tokens": 30, "output_tokens": 3},
        ),
    ])

    turns, _, _ = run_agent_loop(
        agent=agent,
        messages=messages,
        tool_executor=fake_tool_executor,
        max_turns=30,
    )

    assert turns == 3
    # system, user, (asst#1, tool#1), (asst#2, tool#2), asst#3
    assert [m.role for m in messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
        "tool",
        "assistant",
    ]
    # Every assistant message has content we can read
    assistant_contents = [m.content for m in messages if m.role == "assistant"]
    assert assistant_contents == ["first action", "second action", "finished"]


def test_max_turns_limit_is_enforced():
    """The loop stops after max_turns iterations even if the agent keeps calling."""
    messages = _initial_messages()
    # Agent that always wants to call bash, never finishes
    def _always_tool_call(_i):
        return AgentResult(
            text="loop forever",
            tool_calls=[BashToolCall(call_id=f"c{_i}", command="echo hi")],
            usage={"input_tokens": 1, "output_tokens": 1},
        )
    agent = FakeAgent([_always_tool_call(i) for i in range(100)])

    turns, _, _ = run_agent_loop(
        agent=agent,
        messages=messages,
        tool_executor=fake_tool_executor,
        max_turns=5,
    )

    assert turns == 5
    # Every turn produced an assistant message and a tool message, so total
    # messages = 2 (system+user) + 5 * 2 (assistant+tool) = 12
    assert len(messages) == 12


def test_deadline_stops_loop_early():
    """An already-expired deadline stops the loop before calling the agent."""
    messages = _initial_messages()
    agent = FakeAgent([
        AgentResult(
            text="should not run",
            tool_calls=[BashToolCall(call_id="c1", command="echo")],
            usage={},
        ),
    ])

    # Deadline already passed
    turns, _, _ = run_agent_loop(
        agent=agent,
        messages=messages,
        tool_executor=fake_tool_executor,
        max_turns=30,
        deadline=0.0,  # 1970
    )

    assert turns == 0
    assert agent.call_count == 0
    assert len(messages) == 2  # untouched


def test_empty_text_response_still_records_assistant_message():
    """Even when the model returns empty text with no tool calls, we record it."""
    messages = _initial_messages()
    agent = FakeAgent([
        AgentResult(text=None, tool_calls=[], usage={}),
    ])

    turns, _, _ = run_agent_loop(
        agent=agent,
        messages=messages,
        tool_executor=fake_tool_executor,
    )

    assert turns == 1
    assert len(messages) == 3
    assert messages[2].role == "assistant"
    assert messages[2].content == ""  # normalized to empty string
