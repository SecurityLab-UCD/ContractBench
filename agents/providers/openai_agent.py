"""OpenAI-compatible LLM agent (GPT-4o, Together AI, etc.).

Reads OPENAI_API_KEY (or TOGETHER_API_KEY) from environment.
Uses the OpenAI Python SDK's chat.completions.create with tool_choice="auto".
"""

from __future__ import annotations

import json
import os
from typing import Any, List

from agents.base import AgentResult, BashToolCall, LLMAgent, Message


class OpenAIAgent(LLMAgent):
    """Agent using the OpenAI chat completions API."""

    provider = "openai"

    def __init__(self, model: str, **kwargs: Any):
        super().__init__(model, **kwargs)

        import openai

        api_key = kwargs.get("api_key") or os.environ.get("OPENAI_API_KEY")
        base_url = kwargs.get("base_url") or os.environ.get("OPENAI_BASE_URL")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set. Add it to your .env file:\n"
                "  OPENAI_API_KEY=sk-..."
            )

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = openai.OpenAI(**client_kwargs)

    def generate(self, messages: List[Message]) -> AgentResult:
        oai_messages = _to_openai_messages(messages)
        tools = [_bash_tool_openai()]

        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        if self.model.startswith("gpt-5"):
            request_kwargs["max_completion_tokens"] = self.max_tokens
        else:
            request_kwargs["temperature"] = self.temperature
            request_kwargs["max_tokens"] = self.max_tokens

        response = self._client.chat.completions.create(**request_kwargs)

        choice = response.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    # Model hit max_tokens mid-JSON (truncated function arguments)
                    args = {}
                tool_calls.append(BashToolCall(
                    call_id=tc.id,
                    command=args.get("command", ""),
                ))

        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }

        return AgentResult(
            text=msg.content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            usage=usage,
        )


class TogetherAgent(OpenAIAgent):
    """Agent using Together AI (OpenAI-compatible API)."""

    provider = "together"

    def __init__(self, model: str, **kwargs: Any):
        api_key = kwargs.get("api_key") or os.environ.get("TOGETHER_API_KEY")
        base_url = kwargs.get("base_url") or os.environ.get(
            "TOGETHER_BASE_URL", "https://api.together.xyz/v1"
        )
        if not api_key:
            raise ValueError(
                "TOGETHER_API_KEY not set. Add it to your .env file:\n"
                "  TOGETHER_API_KEY=..."
            )
        kwargs["api_key"] = api_key
        kwargs["base_url"] = base_url
        super().__init__(model, **kwargs)


class HuggingFaceAgent(OpenAIAgent):
    """Agent using Hugging Face Inference API (OpenAI-compatible).

    Free tier: $0.10/month credits, ~300 requests/hour.
    Supports Qwen, Llama, DeepSeek, and 200+ models.
    Get token at: https://huggingface.co/settings/tokens
    """

    provider = "huggingface"

    def __init__(self, model: str, **kwargs: Any):
        api_key = kwargs.get("api_key") or os.environ.get("HF_TOKEN")
        base_url = kwargs.get("base_url") or os.environ.get(
            "HF_BASE_URL", "https://router.huggingface.co/v1"
        )
        if not api_key:
            raise ValueError(
                "HF_TOKEN not set. Add it to your .env file:\n"
                "  HF_TOKEN=hf_...\n"
                "Get one at: https://huggingface.co/settings/tokens"
            )
        kwargs["api_key"] = api_key
        kwargs["base_url"] = base_url
        # HF free tier caps max_tokens at 8192
        kwargs.setdefault("max_tokens", 8192)
        super().__init__(model, **kwargs)


class VLLMAgent(OpenAIAgent):
    """Agent using a local vLLM server (OpenAI-compatible).

    Start vLLM: vllm serve <model> --port 8000
    Set VLLM_BASE_URL if not using default http://localhost:8000/v1.
    """

    provider = "vllm"

    def __init__(self, model: str, **kwargs: Any):
        base_url = kwargs.get("base_url") or os.environ.get(
            "VLLM_BASE_URL", "http://localhost:8000/v1"
        )
        # vLLM doesn't require an API key but openai client needs one
        kwargs.setdefault("api_key", "EMPTY")
        kwargs["base_url"] = base_url
        super().__init__(model, **kwargs)


def _bash_tool_openai() -> dict:
    """Return bash tool in OpenAI function-calling format."""
    from agents.base import BASH_TOOL_DEFINITION

    return {
        "type": "function",
        "function": BASH_TOOL_DEFINITION,
    }


def _to_openai_messages(messages: List[Message]) -> list[dict]:
    """Convert internal Message format to OpenAI API format."""
    oai: list[dict] = []
    for m in messages:
        if m.role == "tool":
            oai.append({
                "role": "tool",
                "tool_call_id": m.tool_call_id,
                "content": m.content,
            })
        elif m.role == "assistant" and m.tool_calls:
            tc_list = [
                {
                    "id": tc.call_id,
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": json.dumps({"command": tc.command}),
                    },
                }
                for tc in m.tool_calls
            ]
            oai.append({
                "role": "assistant",
                "content": m.content or None,
                "tool_calls": tc_list,
            })
        else:
            oai.append({"role": m.role, "content": m.content})
    return oai
