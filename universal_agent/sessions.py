"""Session linker for cross-platform continuity.

Maps a canonical user identity to a shared agent session ID.
Each interface keeps its own session for platform-specific features
(Slack threads, Telegram reply chains), but the agent sees a unified
session for memory and learning continuity.
"""


def get_agent_session_id(canonical_user_id: str) -> str:
    """Derive a deterministic agent session from canonical user ID.

    This session is shared across platforms: memories saved on Slack
    are recalled on Telegram because both resolve to the same session.
    """
    return f"universal:{canonical_user_id}"
