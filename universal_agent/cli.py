# Standalone CLI entrypoint
# Run: python -m universal_agent.cli

import os

from universal_agent.agent import create_agent
from universal_agent.identity import canonicalize, get_agent_session_id
from universal_agent.tools import ToolTier


def main():
    raw_user = os.getenv("UNIVERSAL_AGENT_USER", "local-user")
    canonical = canonicalize("cli", raw_user)
    session_id = get_agent_session_id(canonical)

    tier = ToolTier(os.getenv("UNIVERSAL_AGENT_TOOLS", "3"))  # default: privileged

    agent = create_agent(
        user_id=canonical,
        session_id=session_id,
        tool_tier=tier,
    )
    agent.cli_app(stream=True)


if __name__ == "__main__":
    main()
