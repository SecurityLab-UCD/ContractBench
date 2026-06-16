"""Tests for the agents/ module: config, base classes, model parsing."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from agents.base import BASH_TOOL_DEFINITION, SYSTEM_PROMPT, AgentResult, BashToolCall, Message
from agents.config import MODEL_ALIASES, _PROVIDER_REGISTRY, parse_model_string


# ── Message ────────────────────────────────────────────────────────────


class TestMessage:
    def test_basic_message(self):
        m = Message(role="user", content="hello")
        assert m.role == "user"
        assert m.content == "hello"
        assert m.tool_call_id is None

    def test_tool_message(self):
        m = Message(role="tool", content="output", tool_call_id="tc_123")
        d = m.to_dict()
        assert d["role"] == "tool"
        assert d["tool_call_id"] == "tc_123"

    def test_to_dict(self):
        m = Message(role="assistant", content="thinking")
        d = m.to_dict()
        assert d == {"role": "assistant", "content": "thinking"}
        assert "tool_call_id" not in d


# ── BashToolCall ───────────────────────────────────────────────────────


class TestBashToolCall:
    def test_basic(self):
        tc = BashToolCall(call_id="id_1", command="curl http://localhost:8080")
        assert tc.call_id == "id_1"
        assert "curl" in tc.command


# ── AgentResult ────────────────────────────────────────────────────────


class TestAgentResult:
    def test_done_when_no_tool_calls(self):
        r = AgentResult(text="DONE")
        assert r.is_done
        assert not r.wants_tool_execution

    def test_not_done_with_tool_calls(self):
        r = AgentResult(
            text="running",
            tool_calls=[BashToolCall(call_id="1", command="ls")],
        )
        assert not r.is_done
        assert r.wants_tool_execution

    def test_empty_result(self):
        r = AgentResult()
        assert r.is_done
        assert r.text is None
        assert r.tool_calls == []
        assert r.usage == {}


# ── parse_model_string ─────────────────────────────────────────────────


class TestParseModelString:
    def test_full_format(self):
        provider, model = parse_model_string("openai/gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_anthropic_format(self):
        provider, model = parse_model_string("anthropic/claude-sonnet-4-5-20250929")
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-5-20250929"

    def test_together_with_slashes(self):
        provider, model = parse_model_string("together/meta-llama/Llama-3.1-70B")
        assert provider == "together"
        assert model == "meta-llama/Llama-3.1-70B"

    def test_alias_resolution(self):
        provider, model = parse_model_string("gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_claude_alias(self):
        provider, model = parse_model_string("claude-sonnet")
        assert provider == "anthropic"
        assert "claude" in model

    def test_unknown_model_no_slash(self):
        with pytest.raises(ValueError, match="Unknown model"):
            parse_model_string("unknown-model-xyz")

    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            parse_model_string("fake_provider/some-model")

    def test_all_aliases_resolve(self):
        for alias in MODEL_ALIASES:
            provider, model = parse_model_string(alias)
            assert provider in _PROVIDER_REGISTRY
            assert len(model) > 0


# ── BASH_TOOL_DEFINITION ──────────────────────────────────────────────


class TestBashToolDefinition:
    def test_has_required_fields(self):
        assert "name" in BASH_TOOL_DEFINITION
        assert BASH_TOOL_DEFINITION["name"] == "bash"
        assert "description" in BASH_TOOL_DEFINITION
        assert "parameters" in BASH_TOOL_DEFINITION

    def test_parameters_schema(self):
        params = BASH_TOOL_DEFINITION["parameters"]
        assert params["type"] == "object"
        assert "command" in params["properties"]
        assert "command" in params["required"]


# ── SYSTEM_PROMPT ──────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_mentions_bash(self):
        assert "bash" in SYSTEM_PROMPT.lower()

    def test_mentions_localhost(self):
        assert "localhost:8080" in SYSTEM_PROMPT

    def test_mentions_preserve(self):
        assert "preserve" in SYSTEM_PROMPT.lower() or "Preserve" in SYSTEM_PROMPT


# ── Provider registry ─────────────────────────────────────────────────


class TestProviderRegistry:
    def test_all_four_providers(self):
        assert "openai" in _PROVIDER_REGISTRY
        assert "anthropic" in _PROVIDER_REGISTRY
        assert "google" in _PROVIDER_REGISTRY
        assert "together" in _PROVIDER_REGISTRY

    def test_registry_entries_are_tuples(self):
        for name, (module, cls) in _PROVIDER_REGISTRY.items():
            assert isinstance(module, str)
            assert isinstance(cls, str)
            assert "." in module  # Should be a dotted module path


# ── create_agent (mock-based) ─────────────────────────────────────────


class TestCreateAgent:
    def test_missing_api_key_raises(self):
        """create_agent should raise ValueError when API key is missing."""
        from agents.config import create_agent

        env = {k: v for k, v in os.environ.items() if "API_KEY" not in k}
        with patch.dict(os.environ, env, clear=True):
            # Also prevent _load_dotenv from reading .env file
            with patch("agents.config._load_dotenv"):
                with pytest.raises(ValueError, match="API_KEY"):
                    create_agent("openai/gpt-4o")

    def test_missing_anthropic_key_raises(self):
        from agents.config import create_agent

        env = {k: v for k, v in os.environ.items() if "API_KEY" not in k}
        with patch.dict(os.environ, env, clear=True):
            with patch("agents.config._load_dotenv"):
                with pytest.raises(ValueError, match="API_KEY"):
                    create_agent("anthropic/claude-sonnet-4-5-20250929")
