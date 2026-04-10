# Tool assembly with risk tiers
#
# SAFE         — always loaded (web search, read-only file ops)
# PRODUCTIVITY — loaded when credentials exist (GitHub, Exa, image gen)
# PRIVILEGED   — loaded only on trusted interfaces (shell, code sandbox)

import os
from enum import IntEnum
from typing import List


class ToolTier(IntEnum):
    SAFE = 1
    PRODUCTIVITY = 2
    PRIVILEGED = 3


def get_tools(tier: ToolTier = ToolTier.SAFE, db=None) -> List:
    tools = []

    from agno.tools.duckduckgo import DuckDuckGoTools
    from agno.tools.file import FileTools

    tools.append(DuckDuckGoTools())
    tools.append(FileTools())

    try:
        from agno.tools.crawl4ai import Crawl4aiTools
        tools.append(Crawl4aiTools(max_length=5000))
    except ImportError:
        pass

    if tier >= ToolTier.PRODUCTIVITY:
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

    if tier >= ToolTier.PRIVILEGED:
        from agno.tools.shell import ShellTools
        tools.append(ShellTools())

        if os.getenv("E2B_API_KEY"):
            try:
                from agno.tools.e2b import E2BTools
                tools.append(E2BTools())
            except ImportError:
                pass

    if db is not None:
        from agno.tools.scheduler import SchedulerTools
        tools.append(SchedulerTools(db=db))

    return tools
