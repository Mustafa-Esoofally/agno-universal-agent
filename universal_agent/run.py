"""AgentOS server — multi-interface entrypoint.

Starts a FastAPI server with Slack, Telegram, WhatsApp, and AGUI
interfaces, plus cron scheduling. Each interface is enabled only
when its credentials are present in the environment.

Run: python -m universal_agent.run
"""

import os

from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

from universal_agent.agent import create_agent
from universal_agent.db import get_db
from universal_agent.tools import ToolTier


def build_app() -> AgentOS:
    db = get_db()

    # Server-facing agent uses SAFE tier by default for messaging
    # Users can override via UNIVERSAL_AGENT_SERVER_TOOLS
    tier_str = os.getenv("UNIVERSAL_AGENT_SERVER_TOOLS", "safe")
    tier = ToolTier(tier_str)
    agent = create_agent(tool_tier=tier)

    interfaces = []

    # AGUI (web interface) — always available
    interfaces.append(AGUI(agent=agent))

    # Slack — requires bot token + signing secret
    if os.getenv("SLACK_BOT_TOKEN") and os.getenv("SLACK_SIGNING_SECRET"):
        from agno.os.interfaces.slack import Slack
        interfaces.append(Slack(
            agent=agent,
            resolve_user_identity=True,
        ))

    # Telegram — requires bot token
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from agno.os.interfaces.telegram import Telegram
        interfaces.append(Telegram(
            agent=agent,
            streaming=True,
        ))

    # WhatsApp — requires access token + phone number ID
    if os.getenv("WHATSAPP_ACCESS_TOKEN") and os.getenv("WHATSAPP_PHONE_NUMBER_ID"):
        from agno.os.interfaces.whatsapp import Whatsapp
        interfaces.append(Whatsapp(agent=agent))

    return AgentOS(
        name="Universal Agent",
        agents=[agent],
        interfaces=interfaces,
        db=db,
        scheduler=True,
        run_hooks_in_background=True,
    )


app = build_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7777"))
    uvicorn.run("universal_agent.run:app", host="0.0.0.0", port=port, reload=True)
