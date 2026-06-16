"""Agent configuration: .env loading and provider registry.

Usage:
    agent = create_agent("openai/gpt-4o")
    agent = create_agent("anthropic/claude-sonnet-4-5-20250929")
    agent = create_agent("together/meta-llama/Llama-3.1-70B-Instruct-Turbo")
    agent = create_agent("google/gemini-1.5-pro")
    agent = create_agent("huggingface/Qwen/Qwen2.5-72B-Instruct")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agents.base import LLMAgent


def _load_dotenv() -> None:
    """Load .env file from project root if it exists."""
    root = Path(__file__).resolve().parents[1]
    env_file = root / ".env"
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Don't override existing env vars
            if key and value and key not in os.environ:
                os.environ[key] = value


# Provider shorthand → (module, class)
_PROVIDER_REGISTRY: dict[str, tuple[str, str]] = {
    "openai": ("agents.providers.openai_agent", "OpenAIAgent"),
    "anthropic": ("agents.providers.anthropic_agent", "AnthropicAgent"),
    "google": ("agents.providers.google_agent", "GoogleAgent"),
    "together": ("agents.providers.openai_agent", "TogetherAgent"),
    "huggingface": ("agents.providers.openai_agent", "HuggingFaceAgent"),
    "vllm": ("agents.providers.openai_agent", "VLLMAgent"),
}

# Convenient model aliases: short name → provider/model
MODEL_ALIASES: dict[str, str] = {
    # OpenAI GPT-4 series
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4.1": "openai/gpt-4.1",
    "gpt-4.1-mini": "openai/gpt-4.1-mini",
    # OpenAI GPT-5 series
    "gpt-5": "openai/gpt-5",
    "gpt-5-mini": "openai/gpt-5-mini",
    "gpt-5.1": "openai/gpt-5.1",
    "gpt-5.2": "openai/gpt-5.2",
    # Anthropic Claude series
    "claude-sonnet": "anthropic/claude-sonnet-4-5-20250929",
    "claude-haiku": "anthropic/claude-haiku-4-5-20251001",
    "claude-opus": "anthropic/claude-opus-4-6",
    # Google Gemini series
    "gemini-1.5-pro": "google/gemini-1.5-pro",
    "gemini-2.0-flash": "google/gemini-2.0-flash",
    # Open-source (Together AI)
    "llama-3.1-70b": "together/meta-llama/Llama-3.1-70B-Instruct-Turbo",
    "llama-3.1-8b": "together/meta-llama/Llama-3.1-8B-Instruct-Turbo",
    "llama-3.3-70b": "together/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "llama-3.1-405b": "together/meta-llama/Llama-3.1-405B-Instruct-Turbo",
    "qwen-2.5-72b": "together/Qwen/Qwen2.5-72B-Instruct-Turbo",
    "deepseek-r1": "together/deepseek-ai/DeepSeek-R1",
    "mixtral-8x22b": "together/mistralai/Mixtral-8x22B-Instruct-v0.1",
    # Open-source (Hugging Face Inference API)
    "hf-qwen-2.5-72b": "huggingface/Qwen/Qwen2.5-72B-Instruct",
    "hf-llama-3.1-70b": "huggingface/meta-llama/Llama-3.1-70B-Instruct",
    "hf-llama-3.3-70b": "huggingface/meta-llama/Llama-3.3-70B-Instruct",
    "hf-deepseek-v3": "huggingface/deepseek-ai/DeepSeek-V3-0324",
    "hf-qwen-3-235b": "huggingface/Qwen/Qwen3-235B-A22B",
    "hf-qwen-3.5-397b": "huggingface/Qwen/Qwen3.5-397B-A17B",
    # Open-source (vLLM local serving — OpenAI-compatible)
    "vllm-llama-3.3-70b": "vllm/meta-llama/Llama-3.3-70B-Instruct",
    "vllm-gemma-2-27b": "vllm/google/gemma-2-27b-it",
    "vllm-phi-4-14b": "vllm/microsoft/phi-4",
    "vllm-mistral-large": "vllm/mistralai/Mistral-Large-Instruct-2411",
    "vllm-mixtral-8x22b": "vllm/mistralai/Mixtral-8x22B-Instruct-v0.1",
    # Google Gemini (free via AI Studio)
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.5-pro": "google/gemini-2.5-pro",
}


def parse_model_string(model_str: str) -> tuple[str, str]:
    """Parse 'provider/model' string into (provider, model_id).

    Also resolves short aliases like 'gpt-4o' → ('openai', 'gpt-4o').
    """
    # Check aliases first
    if model_str in MODEL_ALIASES:
        model_str = MODEL_ALIASES[model_str]

    if "/" not in model_str:
        raise ValueError(
            f"Unknown model: {model_str!r}. Use 'provider/model' format "
            f"(e.g., 'openai/gpt-4o') or a known alias: {sorted(MODEL_ALIASES.keys())}"
        )

    provider, _, model_id = model_str.partition("/")
    if provider not in _PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown provider: {provider!r}. "
            f"Available: {sorted(_PROVIDER_REGISTRY.keys())}"
        )
    return provider, model_id


def create_agent(model_str: str, **kwargs: Any) -> LLMAgent:
    """Create an LLM agent from a model string.

    Args:
        model_str: Either 'provider/model' (e.g., 'openai/gpt-4o')
                   or a short alias (e.g., 'gpt-4o').
        **kwargs: Passed to the agent constructor (temperature, max_tokens, api_key, etc.)

    Returns:
        LLMAgent instance ready to call .generate().
    """
    _load_dotenv()

    provider, model_id = parse_model_string(model_str)
    module_path, class_name = _PROVIDER_REGISTRY[provider]

    import importlib
    module = importlib.import_module(module_path)
    agent_cls = getattr(module, class_name)

    return agent_cls(model_id, **kwargs)


def list_providers() -> list[str]:
    """Return list of available provider names."""
    return sorted(_PROVIDER_REGISTRY.keys())
