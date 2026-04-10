import os
from pathlib import Path
from typing import Optional

_DEFAULT_SOUL_PATH = Path(__file__).resolve().parent.parent / "SOUL.md"


def load_persona(path: Optional[str] = None) -> str:
    soul_path = Path(
        path
        or os.getenv("UNIVERSAL_AGENT_SOUL_PATH")
        or _DEFAULT_SOUL_PATH
    )
    if soul_path.is_file():
        return soul_path.read_text().strip()

    return (
        "You are a personal AI assistant. "
        "Use tools to take action. Remember details about the user."
    )
