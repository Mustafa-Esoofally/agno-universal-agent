# Autonomous skill extraction post-hook
#
# Runs in background after every agent response (run_hooks_in_background=True).
# Inspects the response for multi-tool procedural work. Currently a gate —
# the actual extraction is handled by LearningMachine's ALWAYS-mode processing.
# Can be extended to spawn a review agent that calls save_learning().

from agno.utils.log import log_debug

_SKIP_TOOLS = frozenset({"run_shell_command", "run_python_code", "run_command"})


async def skill_extraction_hook(run_output, agent) -> None:
    if run_output is None:
        return

    learning = agent.learning_machine
    if learning is None:
        return

    if getattr(learning, "learned_knowledge_store", None) is None:
        return

    # Use RunOutput.tools — each ToolExecution has .tool_name
    tool_names = [t.tool_name for t in (run_output.tools or []) if t.tool_name]
    if len(tool_names) < 2:
        return

    # Don't auto-save procedures involving shell/code execution
    if _SKIP_TOOLS & set(tool_names):
        log_debug("Skill extraction: skipping — privileged tools involved")
        return

    log_debug(f"Skill extraction: {len(tool_names)} tool calls eligible")
    # LearningMachine's process() in _managers.py handles the extraction
    # for ALWAYS-mode stores. AGENTIC stores rely on the agent's own
    # save_learning tool during the conversation.
