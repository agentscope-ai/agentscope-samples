# -*- coding: utf-8 -*-
"""
AgentScope Native Model Factory
Uses native AgentScope model classes for LLM calls
"""
import os
from enum import Enum
from typing import Optional, Tuple
from agentscope.formatter import (
    AnthropicChatFormatter,
    DashScopeChatFormatter,
    GeminiChatFormatter,
    OllamaChatFormatter,
    OpenAIChatFormatter,
)
from agentscope.model import (
    AnthropicChatModel,
    DashScopeChatModel,
    GeminiChatModel,
    OllamaChatModel,
    OpenAIChatModel,
)


class ModelProvider(Enum):
    """Supported model providers"""

    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    DASHSCOPE = "DASHSCOPE"
    ALIBABA = "ALIBABA"
    GEMINI = "GEMINI"
    GOOGLE = "GOOGLE"
    OLLAMA = "OLLAMA"
    DEEPSEEK = "DEEPSEEK"
    GROQ = "GROQ"
    OPENROUTER = "OPENROUTER"


# Provider to AgentScope model class mapping
PROVIDER_MODEL_MAP = {
    "OPENAI": OpenAIChatModel,
    "ANTHROPIC": AnthropicChatModel,
    "DASHSCOPE": DashScopeChatModel,
    "ALIBABA": DashScopeChatModel,
    "GEMINI": GeminiChatModel,
    "GOOGLE": GeminiChatModel,
    "OLLAMA": OllamaChatModel,
    # OpenAI-compatible providers use OpenAIChatModel with custom base_url
    "DEEPSEEK": OpenAIChatModel,
    "GROQ": OpenAIChatModel,
    "OPENROUTER": OpenAIChatModel,
}

# Provider to formatter mapping
PROVIDER_FORMATTER_MAP = {
    "OPENAI": OpenAIChatFormatter,
    "ANTHROPIC": AnthropicChatFormatter,
    "DASHSCOPE": DashScopeChatFormatter,
    "ALIBABA": DashScopeChatFormatter,
    "GEMINI": GeminiChatFormatter,
    "GOOGLE": GeminiChatFormatter,
    "OLLAMA": OllamaChatFormatter,
    # OpenAI-compatible providers use OpenAIChatFormatter
    "DEEPSEEK": OpenAIChatFormatter,
    "GROQ": OpenAIChatFormatter,
    "OPENROUTER": OpenAIChatFormatter,
}

# Provider-specific base URLs
PROVIDER_BASE_URLS = {
    "DEEPSEEK": "https://api.deepseek.com/v1",
    "GROQ": "https://api.groq.com/openai/v1",
    "OPENROUTER": "https://openrouter.ai/api/v1",
}

# Provider-specific API key environment variable names
PROVIDER_API_KEY_ENV = {
    "OPENAI": "OPENAI_API_KEY",
    "ANTHROPIC": "ANTHROPIC_API_KEY",
    "DASHSCOPE": "DASHSCOPE_API_KEY",
    "ALIBABA": "DASHSCOPE_API_KEY",
    "GEMINI": "GOOGLE_API_KEY",
    "GOOGLE": "GOOGLE_API_KEY",
    "DEEPSEEK": "DEEPSEEK_API_KEY",
    "GROQ": "GROQ_API_KEY",
    "OPENROUTER": "OPENROUTER_API_KEY",
}


def create_model(
    model_name: str,
    provider: str,
    api_key: Optional[str] = None,
    stream: bool = False,
    **kwargs,
):
    """
    Create an AgentScope model instance

    Args:
        model_name: Model name (e.g., "gpt-4o", "claude-3-opus")
        provider: Provider name (e.g., "OPENAI", "ANTHROPIC")
        api_key: API key (optional, will read from env if not provided)
        stream: Whether to use streaming mode
        **kwargs: Additional model-specific arguments

    Returns:
        AgentScope model instance
    """
    provider = provider.upper()

    model_class = PROVIDER_MODEL_MAP.get(provider)
    if model_class is None:
        raise ValueError(f"Unsupported provider: {provider}")

    # Get API key from env if not provided
    if api_key is None:
        env_key = PROVIDER_API_KEY_ENV.get(provider)
        if env_key:
            api_key = os.getenv(env_key)

    # Build model kwargs
    model_kwargs = {
        "model_name": model_name,
        "stream": stream,
        **kwargs,
    }

    # Add API key if needed (Ollama doesn't need it)
    if provider != "OLLAMA" and api_key:
        model_kwargs["api_key"] = api_key

    # Handle OpenAI-compatible providers with custom base_url
    if provider in PROVIDER_BASE_URLS:
        base_url = PROVIDER_BASE_URLS[provider]
        model_kwargs["client_args"] = {"base_url": base_url}

    # Handle custom OpenAI base URL
    if provider == "OPENAI":
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
        if base_url:
            model_kwargs["client_args"] = {"base_url": base_url}

    # Handle DashScope base URL (uses different parameter)
    if provider in ("DASHSCOPE", "ALIBABA"):
        base_url = os.getenv("DASHSCOPE_BASE_URL")
        if base_url:
            model_kwargs["base_http_api_url"] = base_url

    # Handle Ollama host
    if provider == "OLLAMA":
        host = os.getenv("OLLAMA_HOST")
        if host:
            model_kwargs["host"] = host

    return model_class(**model_kwargs)


def get_agent_model(agent_id: str, stream: bool = False):
    """
    Get model for a specific agent based on environment variables

    Environment variable pattern:
        AGENT_{AGENT_ID}_MODEL_NAME: Model name
        AGENT_{AGENT_ID}_MODEL_PROVIDER: Provider name

    fallback to global MODEL_NAME & MODEL_PROVIDER if agent-specific not given

    Args:
        agent_id: Agent ID (e.g., "sentiment_analyst", "portfolio_manager")
        stream: Whether to use streaming mode

    Returns:
        AgentScope model instance
    """
    # Normalize agent_id to uppercase for env var lookup
    agent_key = agent_id.upper().replace("-", "_")

    # Try agent-specific config first
    model_name = os.getenv(f"AGENT_{agent_key}_MODEL_NAME")
    provider = os.getenv(f"AGENT_{agent_key}_MODEL_PROVIDER")

    print(f"Using specific model {model_name} for agent {agent_key}")
    # Fall back to global config
    if not model_name:
        model_name = os.getenv("MODEL_NAME", "gpt-4o")
    if not provider:
        provider = os.getenv("MODEL_PROVIDER", "OPENAI")

    return create_model(
        model_name=model_name,
        provider=provider,
        stream=stream,
    )


def get_agent_formatter(agent_id: str):
    """
    Get formatter for a specific agent based on environment variables

    Args:
        agent_id: Agent ID (e.g., "sentiment_analyst", "portfolio_manager")

    Returns:
        AgentScope formatter instance
    """
    # Normalize agent_id to uppercase for env var lookup
    agent_key = agent_id.upper().replace("-", "_")

    # Try agent-specific config first
    provider = os.getenv(f"AGENT_{agent_key}_MODEL_PROVIDER")

    # Fall back to global config
    if not provider:
        provider = os.getenv("MODEL_PROVIDER", "OPENAI")

    provider = provider.upper()
    formatter_class = PROVIDER_FORMATTER_MAP.get(provider, OpenAIChatFormatter)
    return formatter_class()


def get_agent_model_info(agent_id: str) -> Tuple[str, str]:
    """
    Get model name and provider for a specific agent

    Args:
        agent_id: Agent ID (e.g., "sentiment_analyst", "portfolio_manager")

    Returns:
        Tuple of (model_name, provider_name)
    """
    agent_key = agent_id.upper().replace("-", "_")

    model_name = os.getenv(f"AGENT_{agent_key}_MODEL_NAME")
    provider = os.getenv(f"AGENT_{agent_key}_MODEL_PROVIDER")

    if not model_name:
        model_name = os.getenv("MODEL_NAME", "gpt-4o")
    if not provider:
        provider = os.getenv("MODEL_PROVIDER", "OPENAI")

    return model_name, provider.upper()
