# AgentOS server — multi-interface entrypoint
# Run: uvicorn universal_agent.run:app --host 0.0.0.0 --port 7777

import os

from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

from universal_agent.agent import create_agent
from universal_agent.db import get_db, get_knowledge
from universal_agent.tools import ToolTier


def build_app() -> AgentOS:
    db = get_db()
    knowledge = get_knowledge()

    tier_str = os.getenv("UNIVERSAL_AGENT_SERVER_TOOLS", "1")  # default: safe
    tier = ToolTier(int(tier_str))
    agent = create_agent(tool_tier=tier, db=db, knowledge=knowledge)

    interfaces = [AGUI(agent=agent)]

    if os.getenv("SLACK_BOT_TOKEN") and os.getenv("SLACK_SIGNING_SECRET"):
        from agno.os.interfaces.slack import Slack
        interfaces.append(Slack(agent=agent, resolve_user_identity=True))

    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from agno.os.interfaces.telegram import Telegram
        interfaces.append(Telegram(agent=agent, streaming=True))

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


# Module-level: uvicorn resolves "universal_agent.run:app" by importing this module
app = build_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7777"))
    uvicorn.run("universal_agent.run:app", host="0.0.0.0", port=port, reload=True)
