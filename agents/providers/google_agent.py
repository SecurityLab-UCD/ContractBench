"""Google Gemini LLM agent.

Reads GOOGLE_API_KEY from environment.
Uses the google-genai SDK (pip install google-genai).
Falls back to OpenAI-compatible endpoint if google-genai is not installed.
"""

from __future__ import annotations

import json
import os
from typing import Any, List

from agents.base import AgentResult, BashToolCall, LLMAgent, Message


class GoogleAgent(LLMAgent):
    """Agent using Google Gemini via the OpenAI-compatible endpoint.

    Google provides an OpenAI-compatible API at
    https://generativelanguage.googleapis.com/v1beta/openai/
    so we reuse the OpenAI SDK for simplicity.
    """

    provider = "google"

    def __init__(self, model: str, **kwargs: Any):
        super().__init__(model, **kwargs)

        import openai

        api_key = kwargs.get("api_key") or os.environ.get("GOOGLE_API_KEY")
        base_url = kwargs.get("base_url") or os.environ.get(
            "GOOGLE_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not set. Add it to your .env file:\n"
                "  GOOGLE_API_KEY=AIza..."
            )

        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, messages: List[Message]) -> AgentResult:
        from agents.providers.openai_agent import _bash_tool_openai, _to_openai_messages

        oai_messages = _to_openai_messages(messages)
        tools = [_bash_tool_openai()]

        response = self._client.chat.completions.create(
            model=self.model,
            messages=oai_messages,
            tools=tools,
            tool_choice="auto",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        choice = response.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
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
