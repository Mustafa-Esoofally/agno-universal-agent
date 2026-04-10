"""Universal Agent factory.

Composes all modules into a single configured Agent instance:
  db.py       → persistence
  persona.py  → instructions
  learning.py → memory and self-improvement
  tools.py    → tool assembly with risk tiers
  hooks.py    → autonomous skill extraction
"""

import os
from typing import Optional

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.models.fallback import FallbackConfig
from agno.models.openai import OpenAIChat

from universal_agent.db import get_db, get_knowledge
from universal_agent.hooks import skill_extraction_hook
from universal_agent.learning import create_learning
from universal_agent.persona import load_persona
from universal_agent.tools import ToolTier, get_tools


def create_agent(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tool_tier: ToolTier = ToolTier.SAFE,
    model_id: Optional[str] = None,
    soul_path: Optional[str] = None,
) -> Agent:
    """Build a fully-configured Universal Agent.

    Args:
        user_id:    Canonical user identity (from identity.py)
        session_id: Shared session ID (from sessions.py)
        tool_tier:  Which tools to load (safe/productivity/privileged)
        model_id:   Override the default model
        soul_path:  Override the default SOUL.md path
    """
    db = get_db()
    knowledge = get_knowledge()
    learning = create_learning(db=db, knowledge=knowledge)
    tools = get_tools(tier=tool_tier, db=db)
    instructions = load_persona(path=soul_path)

    primary_model_id = model_id or os.getenv("UNIVERSAL_AGENT_MODEL", "gpt-4o-mini")
    primary_model = OpenAIChat(id=primary_model_id)

    # Fallback: try a different provider on errors
    fallback = _build_fallback()

    return Agent(
        name="Universal Agent",
        model=primary_model,
        instructions=instructions,
        tools=tools,
        db=db,
        learning=learning,
        add_learnings_to_context=True,
        # Session
        user_id=user_id,
        session_id=session_id,
        # History and summaries
        add_history_to_context=True,
        num_history_runs=5,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
        # Compression
        compression_manager=CompressionManager(
            compress_tool_results=True,
            compress_tool_results_limit=3,
            compress_token_limit=80_000,
        ),
        # Error recovery
        fallback_config=fallback,
        retries=2,
        exponential_backoff=True,
        # Self-improvement
        post_hooks=[skill_extraction_hook],
        # Output
        markdown=True,
        add_datetime_to_context=True,
    )


def _build_fallback() -> Optional[FallbackConfig]:
    """Build fallback config only if alternative providers are available."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return None

    from agno.models.anthropic import Claude

    return FallbackConfig(
        on_rate_limit=[Claude(id="claude-haiku-4-5-20251001")],
        on_context_overflow=[Claude(id="claude-sonnet-4-20250514")],
        on_error=[Claude(id="claude-sonnet-4-20250514")],
    )
