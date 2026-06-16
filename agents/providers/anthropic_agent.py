"""Anthropic LLM agent (Claude).

Reads ANTHROPIC_API_KEY from environment.
Uses the Anthropic Python SDK's messages.create with tool_use.
"""

from __future__ import annotations

import json
import os
from typing import Any, List

from agents.base import AgentResult, BashToolCall, LLMAgent, Message


class AnthropicAgent(LLMAgent):
    """Agent using the Anthropic Messages API."""

    provider = "anthropic"

    def __init__(self, model: str, **kwargs: Any):
        super().__init__(model, **kwargs)

        import anthropic

        api_key = kwargs.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        base_url = kwargs.get("base_url") or os.environ.get("ANTHROPIC_BASE_URL")

        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Add it to your .env file:\n"
                "  ANTHROPIC_API_KEY=sk-ant-..."
            )

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = anthropic.Anthropic(**client_kwargs)

    def generate(self, messages: List[Message]) -> AgentResult:
        # Anthropic uses a separate system parameter
        system_text = ""
        api_messages: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_text = m.content
            else:
                api_messages.extend(_to_anthropic_message(m))

        tools = [_bash_tool_anthropic()]

        response = self._client.messages.create(
            model=self.model,
            system=system_text,
            messages=api_messages,
            tools=tools,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        # Parse response content blocks
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(BashToolCall(
                    call_id=block.id,
                    command=block.input.get("command", ""),
                ))

        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        return AgentResult(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage=usage,
        )


def _bash_tool_anthropic() -> dict:
    """Return bash tool in Anthropic tool format."""
    from agents.base import BASH_TOOL_DEFINITION

    return {
        "name": BASH_TOOL_DEFINITION["name"],
        "description": BASH_TOOL_DEFINITION["description"],
        "input_schema": BASH_TOOL_DEFINITION["parameters"],
    }


def _to_anthropic_message(m: Message) -> list[dict]:
    """Convert internal Message to Anthropic API message(s)."""
    if m.role == "tool":
        return [{
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": m.tool_call_id,
                "content": m.content,
            }],
        }]

    if m.role == "assistant" and m.tool_calls:
        content: list[dict] = []
        if m.content:
            content.append({"type": "text", "text": m.content})
        for tc in m.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.call_id,
                "name": "bash",
                "input": {"command": tc.command},
            })
        return [{"role": "assistant", "content": content}]

    if m.role == "user":
        return [{"role": "user", "content": m.content}]

    if m.role == "assistant":
        return [{"role": "assistant", "content": m.content}]

    return []
