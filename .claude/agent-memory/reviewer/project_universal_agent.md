---
name: universal-agent codebase patterns
description: Known anti-patterns, DRY violations, and architecture notes for the agno-universal-agent project
type: project
---

_DATA_DIR is defined identically in both db.py and identity.py — canonical source should be db.py, identity.py should import it.

ToolTier enum (tools.py) uses str-valued members but the tier comparison in get_tools() uses tuple membership rather than integer ordering. PRIVILEGED > PRODUCTIVITY > SAFE ordering would be cleaner if ToolTier used IntEnum.

run.py calls build_app() at module level (line 65), which connects to DBs and loads env vars at import time. This is required by uvicorn's import-string pattern ("universal_agent.run:app") but means any test that imports run.py triggers full initialization. The pattern is intentional but should be noted.

hooks.py._SKIP_TOOLS set is recreated inside the function on every call — should be a module-level constant.

skill_extraction_hook (hooks.py) is effectively a no-op gate: it returns early if privileged tools are involved but does nothing substantive afterward (no extraction, no LearningMachine call). The comment admits this is a stub for a future secondary-agent pattern.

identity.py functions unlink(), get_all_links(), link() have no callers in this codebase — dead public API surface.

delivery.py build_delivered_prompt() and build_schedule_payload() have no callers in this codebase — dead code.

sessions.py is a single 17-line file containing one function whose entire body is an f-string. Could be inlined at call sites or merged into identity.py.

agent.py has a docstring on create_agent() — violates no-docstrings rule (CLAUDE.md). The Args block should be removed; the module-level comment already describes the composition.

The db argument in delivery.py build_schedule_payload() is named db but it never appears in that function — the real db consumer is SchedulerTools in tools.py.

**Why:** Gathered during first full review of all 11 modules (2026-04-10).
**How to apply:** Use these findings as baseline when reviewing future PRs against this repo.
