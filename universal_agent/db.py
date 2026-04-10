import os
from pathlib import Path
from typing import Optional

from agno.db.sqlite import SqliteDb


# All local state lives here
DATA_DIR = Path(os.getenv("UNIVERSAL_AGENT_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Singletons — constructed once per process
_db = None
_knowledge = None


def get_db():
    global _db
    if _db is not None:
        return _db

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from agno.db.postgres import PostgresDb
        _db = PostgresDb(db_url=database_url)
    else:
        _db = SqliteDb(db_file=str(DATA_DIR / "agent.db"))
    return _db


def get_knowledge():
    global _knowledge
    if _knowledge is not None:
        return _knowledge

    try:
        from agno.knowledge import Knowledge
        from agno.knowledge.embedder.openai import OpenAIEmbedder
        from agno.vectordb.chroma import ChromaDb, SearchType
    except ImportError:
        return None

    _knowledge = Knowledge(
        name="Agent Learnings",
        vector_db=ChromaDb(
            name="learnings",
            path=str(DATA_DIR / "chromadb"),
            persistent_client=True,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
    )
    return _knowledge
