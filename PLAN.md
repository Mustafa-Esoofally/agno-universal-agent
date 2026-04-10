# Implementation Plan — File by File

> No vibe coding. Each file built in order, tested before moving on.

## Dependency Graph

```
SOUL.md          (standalone — no deps)
  ↓
db.py            (standalone — Agno imports only)
  ↓
persona.py       (standalone — reads SOUL.md from disk)
  ↓
learning.py      (depends on: db.py)
  ↓
identity.py      (standalone — pure logic, no Agno imports)
  ↓
sessions.py      (depends on: identity.py)
  ↓
tools.py         (depends on: db.py)
  ↓
delivery.py      (depends on: tools.py, identity.py)
  ↓
hooks.py         (depends on: learning.py)
  ↓
agent.py         (depends on: ALL above)
  ↓
cli.py           (depends on: agent.py)
  ↓
run.py           (depends on: agent.py, identity.py, sessions.py)
```

## Build Order (13 files)

### File 1: SOUL.md
- **What:** Default persona definition
- **Deps:** None
- **Test:** Read it, verify it's valid markdown
- **Lines:** ~30

### File 2: db.py
- **What:** Database + Knowledge base factory
- **Deps:** agno.db.sqlite, agno.vectordb.chroma, agno.knowledge
- **Exports:** `get_db()`, `get_knowledge()`
- **Key decisions:**
  - Default: SqliteDb (zero-config)
  - Optional: PostgresDb if DATABASE_URL is set
  - ChromaDb for vector search (LearnedKnowledge)
  - OpenAIEmbedder for embeddings
- **Test:** `get_db()` returns a valid db, `get_knowledge()` returns Knowledge with ChromaDb
- **Lines:** ~50

### File 3: persona.py
- **What:** SOUL.md loader
- **Deps:** pathlib only
- **Exports:** `load_persona(path=None) -> str`
- **Key decisions:**
  - Default path: SOUL.md in same directory
  - Override via UNIVERSAL_AGENT_SOUL_PATH env var
  - Returns string content, not parsed structure
- **Test:** Load default SOUL.md, load custom path, handle missing file
- **Lines:** ~20

### File 4: learning.py
- **What:** LearningMachine configuration factory
- **Deps:** db.py, agno.learn
- **Exports:** `create_learning(db, knowledge) -> LearningMachine`
- **Key decisions:**
  - UserProfile: ALWAYS mode (auto-extract name, preferences)
  - UserMemory: ALWAYS mode (auto-capture observations)
  - SessionContext: ALWAYS + enable_planning=True
  - EntityMemory: AGENTIC mode, namespace="user"
  - LearnedKnowledge: AGENTIC mode (only if knowledge provided)
  - Extraction model: gpt-4o-mini (cheap)
- **Test:** Create LearningMachine, verify stores initialized, verify mode settings
- **Lines:** ~60

### File 5: identity.py
- **What:** Cross-platform user identity resolver
- **Deps:** None (pure logic)
- **Exports:** `IdentityResolver` class
- **Key decisions:**
  - Normalize platform IDs to canonical format: `{platform}:{raw_id}`
  - Support explicit linking: `resolver.link("slack:U123", "tg:456")` → same canonical ID
  - Store links in a simple JSON file or DB table
  - Fallback: use platform-native ID if no link exists
- **Test:** Resolve Slack ID, resolve Telegram ID, link two IDs, verify shared canonical
- **Lines:** ~100

### File 6: sessions.py
- **What:** Session linker — maps canonical user to shared agent session
- **Deps:** identity.py
- **Exports:** `get_agent_session_id(canonical_user_id) -> str`
- **Key decisions:**
  - Agent session: `universal:{canonical_user_id}` (shared across platforms)
  - Each interface still uses its own session for threading
  - The agent sees the shared session for memory/learning continuity
- **Test:** Same canonical user → same session; different users → different sessions
- **Lines:** ~30

### File 7: tools.py
- **What:** Tool assembly with risk tiers
- **Deps:** db.py, agno.tools.*
- **Exports:** `get_tools(tier="safe") -> list`, `ToolTier` enum
- **Key decisions:**
  - SAFE (always): DuckDuckGoTools, Crawl4aiTools, FileTools(read-only)
  - PRODUCTIVITY (credential-gated): GithubTools, ExaTools, DalleTools, FalTools, ElevenLabsTools
  - PRIVILEGED (trusted only): ShellTools, E2BTools, FileTools(write)
  - Each tool included only if its env var is set (except SAFE tier)
  - SchedulerTools always included if db is provided
- **Test:** Get safe tools → verify count; get productivity → verify conditional; verify privileged excluded by default
- **Lines:** ~80

### File 8: delivery.py
- **What:** Wraps schedule creation to auto-inject delivery target
- **Deps:** tools.py, identity.py
- **Exports:** `create_delivered_schedule(agent, task, cron, platform, chat_id) -> dict`
- **Key decisions:**
  - Wraps SchedulerTools.create_schedule()
  - Appends delivery instruction to the cron prompt: "After completing the task, use {platform}_tool to send the result to chat {chat_id}"
  - Stores delivery target in schedule payload metadata
  - For CLI-only users: just stores result in DB (no delivery)
- **Test:** Create schedule with Telegram delivery → verify prompt includes "send to Telegram"
- **Lines:** ~50

### File 9: hooks.py
- **What:** Autonomous skill extraction post-hook
- **Deps:** learning.py
- **Exports:** `skill_extraction_hook` async function
- **Key decisions:**
  - Signature: `async def skill_extraction_hook(run_output, agent, session)`
  - Only triggers if run_output has tool calls (procedural work)
  - Searches existing learnings for duplicates before saving
  - Does NOT auto-save shell/code execution procedures (safety)
  - Logs what was saved for debugging
- **Test:** Mock a run_output with tool calls → verify hook attempts save; mock without tools → verify skip
- **Lines:** ~60

### File 10: agent.py
- **What:** Main agent factory — composes everything
- **Deps:** ALL above
- **Exports:** `create_agent(user_id=None, session_id=None, tool_tier="safe") -> Agent`
- **Key decisions:**
  - Model: OpenAIChat(id=os.getenv("UNIVERSAL_AGENT_MODEL", "gpt-4o-mini"))
  - FallbackConfig: on_rate_limit → Claude Haiku, on_error → Claude Sonnet, on_context_overflow → same model
  - CompressionManager: compress after 3 tool results or at 80K tokens
  - enable_session_summaries=True
  - add_learnings_to_context=True
  - post_hooks=[skill_extraction_hook]
  - reasoning=False by default (user can enable)
- **Test:** Create agent → verify tools loaded, learning configured, fallback set, hooks attached
- **Lines:** ~80

### File 11: cli.py
- **What:** Standalone CLI mode (no server needed)
- **Deps:** agent.py
- **Exports:** main() entrypoint
- **Key decisions:**
  - Uses agent.cli_app(stream=True)
  - User identity from UNIVERSAL_AGENT_USER env var
  - Session from UNIVERSAL_AGENT_SESSION or auto-derived from user
  - Tool tier from UNIVERSAL_AGENT_TOOLS env var (default: "safe")
- **Test:** Run with `python cli.py` → verify interactive prompt works
- **Lines:** ~30

### File 12: run.py
- **What:** AgentOS server with multi-interface support
- **Deps:** agent.py, identity.py, sessions.py
- **Exports:** AgentOS app
- **Key decisions:**
  - Interfaces: Slack + Telegram + WhatsApp + AGUI (conditional on env vars)
  - scheduler=True (always enabled if db provided)
  - run_hooks_in_background=True
  - Identity resolution via interface-specific hooks or middleware
- **Test:** Start server → verify /config endpoint → verify interfaces registered
- **Lines:** ~80

### File 13: tests/
- **What:** Unit + integration tests
- **Deps:** All modules
- **Structure:**
  - test_persona.py — SOUL.md loading
  - test_db.py — DB factory
  - test_identity.py — Identity resolution + linking
  - test_sessions.py — Session derivation
  - test_tools.py — Tool tier assembly
  - test_agent.py — Agent creation + configuration
  - test_learning.py — Memory persistence
  - test_hooks.py — Skill extraction hook
  - test_e2e.py — Full stack tests (requires API keys)
- **Lines:** ~300 total

## Total: ~970 lines across 13 files

## Validation Checkpoints

After each file:
1. Import succeeds
2. Unit test passes
3. No circular deps

After File 10 (agent.py):
- Run the P0 prototype test (5/5 must pass)

After File 12 (run.py):
- Start AgentOS server
- Verify /config endpoint
- Test via AGUI web interface

## What We Are NOT Building

- No CLI TUI (rich UI, spinners, skins) — use agent.cli_app()
- No browser automation — add via MCP later
- No RL training pipeline
- No skills marketplace
- No plugin system — Agno Toolkit system handles extensibility
- No Discord interface — doesn't exist in Agno yet
- No prompt injection scanning — should be in Agno core, not here
- No output redaction — should be in Agno core, not here
