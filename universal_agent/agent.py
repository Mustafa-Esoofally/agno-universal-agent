# Universal Agent factory — composes db, persona, learning, tools, and hooks

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
    db=None,
    knowledge=None,
) -> Agent:
    if db is None:
        db = get_db()
    if knowledge is None:
        knowledge = get_knowledge()

    learning = create_learning(db=db, knowledge=knowledge)
    tools = get_tools(tier=tool_tier, db=db)
    instructions = load_persona(path=soul_path)

    primary_model_id = model_id or os.getenv("UNIVERSAL_AGENT_MODEL", "gpt-4o-mini")

    return Agent(
        name="Universal Agent",
        model=OpenAIChat(id=primary_model_id),
        instructions=instructions,
        tools=tools,
        db=db,
        learning=learning,
        add_learnings_to_context=True,
        user_id=user_id,
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=5,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
        compression_manager=CompressionManager(
            compress_tool_results=True,
            compress_tool_results_limit=3,
            compress_token_limit=80_000,
        ),
        fallback_config=_build_fallback(),
        retries=2,
        exponential_backoff=True,
        post_hooks=[skill_extraction_hook],
        markdown=True,
        add_datetime_to_context=True,
    )


def _build_fallback() -> Optional[FallbackConfig]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None

    from agno.models.anthropic import Claude

    # Haiku for rate-limit (cheapest cross-provider), Sonnet for everything else
    return FallbackConfig(
        on_rate_limit=[Claude(id="claude-haiku-4-5-20251001")],
        on_context_overflow=[Claude(id="claude-sonnet-4-20250514")],
        on_error=[Claude(id="claude-sonnet-4-20250514")],
    )
