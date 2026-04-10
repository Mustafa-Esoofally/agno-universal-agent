from typing import Any, Optional

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
    db: Any = None,
    knowledge: Optional[Knowledge] = None,
) -> LearningMachine:
    # Stores: UserProfile + UserMemory (ALWAYS), SessionContext (ALWAYS + planning),
    # EntityMemory (AGENTIC), LearnedKnowledge (AGENTIC, only if knowledge provided).
    # Agent.__init__ auto-injects db and model when not set here.
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

    if knowledge is not None:
        stores["learned_knowledge"] = LearnedKnowledgeConfig(
            mode=LearningMode.AGENTIC,
            knowledge=knowledge,
            enable_agent_tools=True,
        )

    return LearningMachine(db=db, **stores)
