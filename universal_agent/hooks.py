"""Autonomous skill extraction post-hook.

Runs in background after every agent response. Inspects the response
for multi-tool procedural work and saves reusable patterns as
LearnedKnowledge entries via the agent's LearningMachine.

Triggered by: agent post_hooks=[skill_extraction_hook]
Requires: run_hooks_in_background=True on AgentOS (non-blocking)
"""

from agno.utils.log import log_debug, log_warning


async def skill_extraction_hook(run_output, agent) -> None:
    """Analyze completed runs for reusable procedures.

    Only triggers when:
    1. The response involved tool calls (procedural work, not just chat)
    2. The agent has a LearningMachine with a learned_knowledge store
    3. The procedure doesn't involve dangerous operations (shell/code exec)
    """
    if run_output is None:
        return

    learning = agent.learning_machine
    if learning is None:
        return

    # LearnedKnowledge store must be configured
    lk_store = getattr(learning, "learned_knowledge_store", None)
    if lk_store is None:
        return

    # Check if the response had tool calls worth learning from
    tool_calls = _extract_tool_names(run_output)
    if len(tool_calls) < 2:
        # Single tool call or no tools — not enough for a "procedure"
        return

    # Skip if the procedure involved privileged operations
    _SKIP_TOOLS = {"run_shell_command", "run_python_code", "run_command"}
    if _SKIP_TOOLS & set(tool_calls):
        log_debug("Skill extraction: skipping — privileged tools involved")
        return

    log_debug(f"Skill extraction: evaluating {len(tool_calls)} tool calls")

    # Let the LearningMachine's ALWAYS-mode processing handle extraction
    # if it's configured. For AGENTIC mode, we'd need to call tools directly,
    # but the agent already has save_learning in its toolkit — the post-run
    # process() call in _managers.py handles ALWAYS stores.
    #
    # For now, this hook serves as a gate: it could be extended to spawn
    # a secondary agent that reviews the conversation and calls save_learning.
    # That pattern is shown in cookbook/05_agent_os/background_tasks/
    # background_output_evaluation.py


def _extract_tool_names(run_output) -> list:
    """Pull tool call names from a RunOutput."""
    names = []
    messages = getattr(run_output, "messages", None)
    if not messages:
        return names
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                name = getattr(tc, "function", {})
                if isinstance(name, dict):
                    names.append(name.get("name", ""))
                elif hasattr(name, "name"):
                    names.append(name.name)
    return [n for n in names if n]
