---
name: Anti-patterns in universal_agent modules
description: Code reuse issues found in universal_agent/ — _DATA_DIR duplication, _extract_tool_names reinvents RunOutput.tools, module-level app construction side-effect in run.py
type: project
---

## _DATA_DIR defined twice

`db.py:8` and `identity.py:21` both define `_DATA_DIR = Path(os.getenv("UNIVERSAL_AGENT_DATA_DIR", "data"))`.
Should live only in `db.py` and be imported by `identity.py`.

## _extract_tool_names walks messages — use RunOutput.tools instead

`hooks.py:59-74` walks `run_output.messages` and pulls `.tool_calls[].function.name`.
`RunOutput` already has a `.tools: List[ToolExecution]` field where each entry has `.tool_name: str` directly.
The message-walk approach is the wrong level of abstraction; use `run_output.tools`.

**Why:** `RunOutput.tools` is the authoritative flat list of executed tools per run — it's what `agno.utils.response.format_tool_calls` also uses.

## run.py calls build_app() at module level

`run.py:65` calls `build_app()` unconditionally at import time, connecting to the DB and loading credentials.
This means any `import universal_agent.run` in tests or other tooling triggers side-effects.
The standard Agno pattern is to call `build_app()` only inside a guard or a factory.

## identity.py implements identity linking in plain JSON

Agno has no cross-platform identity registry in the framework, so this is intentional app logic.
No Agno equivalent exists to replace it — the pattern is correct as a local JSON file for small deployments.
