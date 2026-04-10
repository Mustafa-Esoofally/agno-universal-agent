import os
from pathlib import Path

from agno.db.sqlite import SqliteDb


# Data directory — all local state lives here
_DATA_DIR = Path(os.getenv("UNIVERSAL_AGENT_DATA_DIR", "data"))


def get_db():
    """Return the session/learning database.

    Uses SqliteDb by default (zero-config). Set DATABASE_URL for Postgres.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from agno.db.postgres import PostgresDb

        return PostgresDb(db_url=database_url)

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file=str(_DATA_DIR / "agent.db"))


def get_knowledge():
    """Return a Knowledge base backed by ChromaDb for LearnedKnowledge.

    ChromaDb stores vectors locally — no server needed.
    Returns None if chromadb is not installed so the agent still works
    without the vector search dependency.
    """
    try:
        from agno.knowledge import Knowledge
        from agno.knowledge.embedder.openai import OpenAIEmbedder
        from agno.vectordb.chroma import ChromaDb, SearchType
    except ImportError:
        return None

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Knowledge(
        name="Agent Learnings",
        vector_db=ChromaDb(
            name="learnings",
            path=str(_DATA_DIR / "chromadb"),
            persistent_client=True,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
    )
