import os
from pathlib import Path


# Default SOUL.md location — sibling of the package directory
_DEFAULT_SOUL_PATH = Path(__file__).resolve().parent.parent / "SOUL.md"


def load_persona(path: str = None) -> str:
    """Load persona instructions from a SOUL.md file.

    Resolution order:
    1. Explicit path argument
    2. UNIVERSAL_AGENT_SOUL_PATH env var
    3. Default SOUL.md shipped with the project
    """
    soul_path = Path(
        path
        or os.getenv("UNIVERSAL_AGENT_SOUL_PATH")
        or _DEFAULT_SOUL_PATH
    )
    if soul_path.is_file():
        return soul_path.read_text().strip()

    # Inline fallback — never crash because a file is missing
    return (
        "You are a personal AI assistant. "
        "Use tools to take action. Remember details about the user."
    )
