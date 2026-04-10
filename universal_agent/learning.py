from typing import Optional

from agno.knowledge import Knowledge
from agno.learn import (
    EntityMemoryConfig,
    LearnedKnowledgeConfig,
    LearningMachine,
    LearningMode,
    SessionContextConfig,
    UserMemoryConfig,
    UserProfileConfig,
)


def create_learning(
    db=None,
    knowledge: Optional[Knowledge] = None,
) -> LearningMachine:
    """Build a LearningMachine with 5 stores.

    Stores and their modes:
      UserProfile      ALWAYS   — silently extract name, role, preferences
      UserMemory       ALWAYS   — silently capture facts and observations
      SessionContext   ALWAYS   — track goals, plans, progress (with planning)
      EntityMemory     AGENTIC  — agent decides when to track external entities
      LearnedKnowledge AGENTIC  — agent decides what procedures to save
                                  (only enabled when a Knowledge base is provided)

    The agent's own model and db are injected automatically by Agent.__init__
    when they are not set here, so we only need to configure modes and flags.
    """
    stores = dict(
        user_profile=UserProfileConfig(mode=LearningMode.ALWAYS),
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
        session_context=SessionContextConfig(
            mode=LearningMode.ALWAYS,
            enable_planning=True,
        ),
        entity_memory=EntityMemoryConfig(
            mode=LearningMode.AGENTIC,
            namespace="user",
        ),
    )

    # LearnedKnowledge requires a vector-backed Knowledge base
    if knowledge is not None:
        stores["learned_knowledge"] = LearnedKnowledgeConfig(
            mode=LearningMode.AGENTIC,
            knowledge=knowledge,
            enable_agent_tools=True,
        )

    return LearningMachine(db=db, **stores)
