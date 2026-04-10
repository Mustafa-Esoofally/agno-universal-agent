"""Tool assembly with risk tiers.

Tools are grouped by safety level so privileged tools (shell, code exec)
are not exposed on untrusted interfaces (public Telegram/Slack bots).

Tiers:
  SAFE         — always loaded, no risk (web search, read-only file ops)
  PRODUCTIVITY — loaded when credentials exist (GitHub, Exa, image gen)
  PRIVILEGED   — loaded only on trusted interfaces (shell, code sandbox)
"""

import os
from enum import Enum
from typing import List


class ToolTier(str, Enum):
    SAFE = "safe"
    PRODUCTIVITY = "productivity"
    PRIVILEGED = "privileged"


def get_tools(tier: ToolTier = ToolTier.SAFE, db=None) -> List:
    """Assemble tools based on the requested trust tier.

    Higher tiers include all lower tiers.
    """
    tools = []

    # -- SAFE: always available, no API keys needed for core search ----------
    from agno.tools.duckduckgo import DuckDuckGoTools
    from agno.tools.file import FileTools

    tools.append(DuckDuckGoTools())
    tools.append(FileTools())

    # Crawl4ai needs the package but no API key
    try:
        from agno.tools.crawl4ai import Crawl4aiTools
        tools.append(Crawl4aiTools(max_length=5000))
    except ImportError:
        pass

    if tier in (ToolTier.PRODUCTIVITY, ToolTier.PRIVILEGED):
        # -- PRODUCTIVITY: credential-gated ----------------------------------
        if os.getenv("EXA_API_KEY"):
            from agno.tools.exa import ExaTools
            tools.append(ExaTools())

        if os.getenv("GITHUB_TOKEN"):
            from agno.tools.github import GithubTools
            tools.append(GithubTools())

        if os.getenv("OPENAI_API_KEY"):
            from agno.tools.dalle import DalleTools
            tools.append(DalleTools())

        if os.getenv("FAL_KEY"):
            from agno.tools.fal import FalTools
            tools.append(FalTools())

        if os.getenv("ELEVEN_API_KEY"):
            from agno.tools.eleven_labs import ElevenLabsTools
            tools.append(ElevenLabsTools())

    if tier == ToolTier.PRIVILEGED:
        # -- PRIVILEGED: trusted interfaces only (CLI, explicit approval) ----
        from agno.tools.shell import ShellTools
        tools.append(ShellTools())

        if os.getenv("E2B_API_KEY"):
            try:
                from agno.tools.e2b import E2BTools
                tools.append(E2BTools())
            except ImportError:
                pass

    # -- SCHEDULER: available if db provided (any tier) ----------------------
    if db is not None:
        from agno.tools.scheduler import SchedulerTools
        tools.append(SchedulerTools(db=db))

    return tools
