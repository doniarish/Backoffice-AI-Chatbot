"""
app/services/llm_service.py
-----------------------------
Centralised LLM client wrapper.

All LangGraph nodes and pipeline steps import `llm` from here,
so the model can be swapped in one place (e.g. gpt-4o → gpt-3.5-turbo).

Configuration (via .env):
    OPENAI_API_KEY   — required for live LLM calls
    LLM_MODEL        — model name (default: gpt-4o-mini)
    LLM_TEMPERATURE  — sampling temperature (default: 0.0 for deterministic SQL)
    LLM_MAX_TOKENS   — max response tokens (default: 1024)

If OPENAI_API_KEY is not set, a stub LLM is returned that raises a clear
error at call time — so tests that mock `llm.invoke` can still run.
"""

import os
import logging

logger = logging.getLogger(__name__)


def _build_llm():
    """Build and return the configured LangChain LLM client."""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    if not api_key:
        logger.warning(
            "[LLMService] OPENAI_API_KEY not set. "
            "LLM calls will fail unless mocked in tests."
        )

    try:
        from langchain_openai import ChatOpenAI
        client = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key or "sk-demo-not-set",
        )
        logger.info("[LLMService] Initialized model=%s temperature=%.1f", model, temperature)
        return client
    except ImportError as exc:
        raise ImportError(
            "langchain-openai is required. Run: pip install langchain-openai"
        ) from exc


# Singleton LLM client — import this throughout the codebase
llm = _build_llm()

