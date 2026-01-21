"""
Unified LLM interface (GPT-Open only)

Provides a very small abstraction to call a GPT-Open compatible server with a
single method. Mistral support has been intentionally removed for simplicity.

Usage:
    text = await a_generate(prompt="Hello")
    text = generate(prompt="Hello")
"""

from __future__ import annotations

import asyncio
import os
from typing import Literal, Optional


ProviderName = Literal["gpt_open"]


def _resolve_provider(requested_provider: Optional[str]) -> ProviderName:
    """Resolve provider; only 'gpt_open' is supported for now."""
    if requested_provider and requested_provider.strip().lower() != "gpt_open":
        raise ValueError("Only 'gpt_open' provider is supported at the moment.")
    return "gpt_open"


async def a_generate(
    prompt: str,
    system: Optional[str] = None,
    provider: Optional[ProviderName] = None,
    model: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    **kwargs,
) -> str:
    """Asynchronously generate text using the selected provider.

    Args:
        prompt: User prompt content.
        system: Optional system instruction.
        provider: "gpt_open" or "mistral". Defaults to env LLM_PROVIDER or "mistral".
        model: Optional model override per provider.
        **kwargs: Provider-specific options (e.g., temperature, max_tokens).

    Returns:
        Generated text content.
    """
    _resolve_provider(provider)

    # Defer blocking HTTP call to a thread to avoid blocking the event loop
    from services.base.gpt_open import GptOpenClient
    from config.settings import settings

    # Use settings with fallback to environment variables
    base_url = settings.gpt_open_base_url
    timeout_seconds = settings.gpt_open_timeout
    default_model = settings.gpt_open_model

    # Get API key from environment
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    client = GptOpenClient(base_url=base_url, timeout=timeout_seconds, model=default_model, api_key=api_key)

    # Get the model to determine which parameters to use
    model_to_use = model or default_model or ""
    is_gpt5_model = "gpt-5" in model_to_use.lower() if model_to_use else False
    is_gpt_oss_20b = "gpt-oss-20b" in model_to_use.lower() if model_to_use else False
    
    # Apply env-driven defaults if not provided by caller
    if "temperature" not in kwargs and not is_gpt5_model:
        # Only add temperature for non-GPT-5 models (GPT-5 only supports default value of 1)
        try:
            kwargs["temperature"] = float(os.environ.get("GPT_OPEN_TEMPERATURE", "0.1"))
        except ValueError:
            kwargs["temperature"] = 0.1
    # Check if we need to add token limit parameters
    if "max_tokens" not in kwargs and "max_completion_tokens" not in kwargs:
        try:
            token_limit = 40000
        except ValueError:
            token_limit = 40000
            
        # Use the appropriate parameter based on the model
        if is_gpt5_model:
            # Do not set any token limit parameters for GPT-5 using chat/completions
            pass
        else:
            # Do not set a hard default for gpt-oss-20b; let downstream heuristic decide
            if not is_gpt_oss_20b:
                kwargs["max_tokens"] = 40000

    # Ensure reasoning_effort is always provided for gpt-oss-20b
    if is_gpt_oss_20b:
        kwargs["reasoning_effort"] = (reasoning_effort or kwargs.get("reasoning_effort") or "low")

    return await asyncio.to_thread(
        client.complete,
        prompt,
        system,
        model,
        **kwargs,
    )


def generate(
    prompt: str,
    system: Optional[str] = None,
    provider: Optional[ProviderName] = None,
    model: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    **kwargs,
) -> str:
    """Synchronous convenience wrapper.

    - Fully supported for provider="gpt_open".
    - For provider="mistral", this will run an event loop if none is running.
      If an event loop is already running, a RuntimeError is raised to avoid
      nested loop issues; use `a_generate` in that case.
    """
    _resolve_provider(provider)

    from services.base.gpt_open import GptOpenClient
    from config.settings import settings

    # Use settings with fallback to environment variables
    base_url = settings.gpt_open_base_url
    timeout_seconds = settings.gpt_open_timeout
    default_model = settings.gpt_open_model

    # Get API key from environment
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    client = GptOpenClient(base_url=base_url, timeout=timeout_seconds, model=default_model, api_key=api_key)

    # Get the model to determine which parameters to use
    model_to_use = model or default_model or ""
    is_gpt5_model = "gpt-5" in model_to_use.lower() if model_to_use else False
    is_gpt_oss_20b = "gpt-oss-20b" in model_to_use.lower() if model_to_use else False
    
    # Apply env-driven defaults if not provided by caller
    if "temperature" not in kwargs and not is_gpt5_model:
        # Only add temperature for non-GPT-5 models (GPT-5 only supports default value of 1)
        try:
            kwargs["temperature"] = float(os.environ.get("GPT_OPEN_TEMPERATURE", "0.1"))
        except ValueError:
            kwargs["temperature"] = 0.1
    # Check if we need to add token limit parameters
    if "max_tokens" not in kwargs and "max_completion_tokens" not in kwargs:
        try:
            token_limit = 40000
        except ValueError:
            token_limit = 40000
            
        # Use the appropriate parameter based on the model
        if is_gpt5_model:
            # Do not set any token limit parameters for GPT-5 using chat/completions
            pass
        else:
            # Do not set a hard default for gpt-oss-20b; let downstream heuristic decide
            if not is_gpt_oss_20b:
                kwargs["max_tokens"] = 40000

    # Ensure reasoning_effort is always provided for gpt-oss-20b
    if is_gpt_oss_20b:
        kwargs["reasoning_effort"] = (reasoning_effort or kwargs.get("reasoning_effort") or "low")

    return client.complete(prompt=prompt, system=system, model=model, **kwargs)


__all__ = ["ProviderName", "a_generate", "generate"]


