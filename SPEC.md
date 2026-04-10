# Agno Universal Agent — Specification

> A personal AI assistant built entirely on Agno. Inspired by Hermes Agent's product experience, powered by Agno's superior architecture.

**Status:** SPEC (no code yet)
**Date:** 2026-04-10
**Author:** Mustafa + Claude analysis (33 research agents, full Hermes source audit)

---

## 1. Vision

A **drop-in personal AI assistant** that:
- Works via CLI, Telegram, Slack, WhatsApp (Discord planned — AgentOS interface not yet built)
- Remembers you across sessions and platforms
- Runs scheduled tasks unattended (morning briefings, repo watchers, system monitors)
- Self-improves by learning reusable procedures
- Executes shell commands, searches the web, generates images, runs sandboxed code
- Recovers from errors with fallback models and context compression
- Customizable persona via a simple markdown file

**Design philosophy:** Hermes-level UX, Agno-level architecture. One command to start, zero configuration required for basic usage, full customization available.

---

## 2. Architecture Decision: Single Agent + Post-Hook Learning

### Why NOT a Team with routing?

Teams add latency (leader must decide which member to route to) and complexity (shared state, member coordination). For a personal assistant handling one user's messages sequentially, a single well-configured agent with all tools is simpler and faster.

**However**, the agent is built as a composable module — users CAN wrap it in a Team or Workflow later. The agent is a building block, not a monolith.

### Why NOT Hermes's approach?

Hermes loads ALL 18 tools on every call (8,759 tokens of tool schemas = 46% overhead). We'll use **tool groups** — configure which tools are active, exclude what you don't need.

### Decision

```
Interface Adapter (Slack/Telegram/WhatsApp/AGUI)
  → Identity Resolver (normalize user_id across platforms)
  → Session Linker (map canonical user_id → shared session)
  → UniversalAgent
      + LearningMachine (5 stores: UserProfile, UserMemory, SessionContext, EntityMemory, LearnedKnowledge)
      + CompressionManager (proactive context compression)
      + FallbackConfig (per-error-type model routing)
      + post_hook (autonomous skill extraction — with approval for dangerous procedures)
      + AgentOS (multi-platform interfaces + scheduler)
```

### Tool Risk Tiers (Codex Recommendation — Adopted)

Tools are gated by interface trust level, not just env vars:

| Tier | Tools | Where Available |
|------|-------|-----------------|
| **Safe** (always) | WebSearch, Crawl4ai, FileTools (read-only), MemoryTools, SchedulerTools | All interfaces |
| **Productivity** (credential-gated) | GithubTools, SlackTools, ExaTools, DalleTools, FalTools, ElevenLabsTools | All interfaces |
| **Privileged** (trusted only) | ShellTools, E2BTools, FileTools (write) | CLI + explicit approval on messaging |

This prevents a random Telegram message from executing `rm -rf /` on your server.

---

## 3. Tool Inventory

### Core Tools (Always Loaded)

| Tool | Agno Class | Readiness | Purpose |
|------|-----------|-----------|---------|
| Web search | `DuckDuckGoTools` | Production | Free web search, no API key |
| Web scraping | `Crawl4aiTools` | Production (async) | Full page content extraction |
| Shell commands | `ShellTools` | Production | Execute local commands |
| File operations | `FileTools` | Production | Read, write, search files |
| Memory | (via LearningMachine) | Production | Persistent user memory |

### Optional Tools (User Enables)

| Tool | Agno Class | Readiness | Purpose | Requires |
|------|-----------|-----------|---------|----------|
| Code sandbox | `E2BTools` | Production | Sandboxed Python execution | `E2B_API_KEY` |
| Semantic search | `ExaTools` | Production | Deep research queries | `EXA_API_KEY` |
| Premium scraping | `FirecrawlTools` | Production | JS-rendered pages | `FIRECRAWL_API_KEY` |
| Image generation | `DalleTools` | Production | Create images | `OPENAI_API_KEY` |
| Image gen (alt) | `FalTools` | Production | FLUX/Hunyuan models | `FAL_KEY` |
| Text-to-speech | `ElevenLabsTools` | Production | Audio generation | `ELEVEN_API_KEY` |
| GitHub ops | `GithubTools` | Production | Issues, PRs, repos | `GITHUB_TOKEN` |
| Slack messaging | `SlackTools` | Production | Send/search Slack | `SLACK_BOT_TOKEN` |
| Telegram messaging | `TelegramTools` | Production | Send media/messages | `TELEGRAM_BOT_TOKEN` |
| Weather | `OpenWeatherTools` | Production | Current + forecast | `OPENWEATHER_API_KEY` |
| Custom APIs | `CustomApiTools` | Production | Any REST API | None |
| Scheduling | `SchedulerTools` | Production (async) | Cron-based automation | DB required |

### Tools NOT Included (Scope Boundary)

| Tool | Why Not |
|------|---------|
| Browser automation | Complex setup, niche use case — add via MCP if needed |
| RL training pipeline | Different product entirely |
| PTY terminal | ShellTools + E2B cover the use cases |
| Mixture of Agents | Niche research feature |
| Home Assistant | Too specialized |

---

## 4. LearningMachine Configuration

### Store Configuration

```
UserProfile     — mode: ALWAYS    — Auto-extract name, preferences, role
UserMemory      — mode: ALWAYS    — Auto-capture facts, observations
SessionContext  — mode: ALWAYS    — Track goals, plans, progress (with planning)
EntityMemory    — mode: AGENTIC   — Agent decides when to track external entities
LearnedKnowledge — mode: AGENTIC  — Agent decides what procedures to save
```

### Rationale

- **UserProfile + UserMemory in ALWAYS mode:** The agent silently learns about you after every conversation — no manual "save this" needed. This is the Hermes "it remembers you" experience.
- **SessionContext with `enable_planning=True`:** Tracks what you're trying to accomplish across turns. When you come back tomorrow, the agent knows where you left off.
- **EntityMemory in AGENTIC mode:** Agent gets `create_entity`, `add_fact`, `add_event` tools. Tracks companies, projects, people you mention — but only when it decides to, not on every turn.
- **LearnedKnowledge in AGENTIC mode:** Agent gets `search_learnings` and `save_learning` tools. This is the "self-improving skills" mechanism. Requires a Knowledge base with vector embeddings.

### Model for Extraction

Use a cheap model (`gpt-4o-mini` or `claude-haiku`) for background extraction. Don't waste the primary model's tokens on learning tasks.

---

## 5. Autonomous Skill Creation (Post-Hook)

### How It Works

```python
async def skill_extraction_hook(run_output, agent, session):
    """Runs in background after every response. Checks if the conversation
    involved tool usage that could be saved as a reusable procedure."""
    
    # Only trigger if tool calls happened (indicates procedural work)
    if not run_output or not has_tool_calls(run_output):
        return
    
    # Search for existing similar learnings (dedup)
    # If novel pattern found, save via LearningMachine
    # The learning contains: problem, approach, tools used, outcome
```

### When It Fires

- After every agent response (via `post_hooks=[skill_extraction_hook]`)
- Only processes responses that involved tool calls
- Runs in background (`run_hooks_in_background=True`) — user gets response immediately
- Checks for duplicates via semantic search before saving

### What Gets Saved

```
Title: "Deploy FastAPI to AWS with ECR + ECS"
Context: "When deploying Python web apps to AWS"
Learning: "1. Build Docker image, 2. Push to ECR, 3. Create ECS task definition..."
Tags: ["aws", "deployment", "docker", "fastapi"]
```

### How It's Recalled

Next time a similar question comes in, `LearningMachine.build_context()` searches the vector store and injects relevant learnings into the system prompt. The agent knows the procedure without re-discovering it.

---

## 6. Cross-Platform Session Continuity

### Problem

Each Agno interface generates its own session_id format:
- Slack: `{entity_id}:{thread_ts}`
- Telegram: `{entity_id}:{user_id}`
- WhatsApp: `{entity_id}:{phone_number}`

Simply overriding to `f"universal:{user_id}"` would break interface-specific session logic (thread tracking, etc.).

### Approach: Identity Resolver + Session Linker (Two Layers)

**Layer 1 — Identity Resolver** (`identity.py`):
Normalizes each platform's user identifier to a canonical `user_id`:

| Platform | Raw ID | Canonical user_id |
|----------|--------|-------------------|
| Slack | Slack user_id → email via `resolve_slack_user()` | `user@example.com` |
| Telegram | Telegram numeric user_id | `tg:123456789` |
| WhatsApp | Phone number | `wa:+15551234567` |
| CLI | `UNIVERSAL_AGENT_USER` env var | `local:mustafa` |
| AGUI | Auth token claim | JWT `sub` claim |

**Layer 2 — Session Linker** (`sessions.py`):
Maps canonical user_id → shared session_id for the agent, while preserving the platform-native session for interface-specific features (Slack threads, Telegram reply chains):

```
agent_session_id = f"universal:{canonical_user_id}"    # Shared across platforms
interface_session_id = platform_native_id               # Per-platform threads
```

The agent sees `agent_session_id` for memory/learning continuity.
The interface sees `interface_session_id` for platform-native UX.

### Result

Same user on Slack and Telegram shares memory, learning, and session context. Platform-specific threading (Slack threads, Telegram reply chains) still works independently.

---

## 7. Persona Customization (SOUL.md)

### Default Persona

```markdown
# Universal Agent

You are a personal AI assistant. You are helpful, concise, and action-oriented.

## Behavior
- Use tools to take action, don't just describe what you would do
- Remember details about the user and apply them in future conversations
- When you discover a reusable pattern, save it as a learning
- Be concise unless the user asks for detail
- Admit when you don't know something

## Capabilities
- Search the web and extract content from pages
- Execute shell commands on the server
- Read, write, and search files
- Remember user preferences and context across sessions
- Schedule recurring tasks
- Generate images and audio (when configured)
```

### Customization

Users create their own `SOUL.md` file to override the default persona. The file is loaded at startup via `instructions=load_persona()`.

---

## 8. Error Recovery

### FallbackConfig

```
Primary:        gpt-4o (or user's chosen model)
on_rate_limit:  claude-sonnet-4 (different provider = different rate limits)
on_context_overflow: gpt-4o-mini (cheaper, same context window)
on_error:       claude-sonnet-4 (general fallback)
```

### CompressionManager

```
compress_tool_results: True
compress_tool_results_limit: 3      # After 3 tool calls, compress old results
compress_token_limit: 80000         # Or when approaching token limit
model: gpt-4o-mini                  # Cheap model for compression
```

### Retry

```
retries: 2
exponential_backoff: True           # 2^attempt seconds, capped at 32s
```

---

## 9. Use Cases (12 Verified)

### Tier 0: Core Experience (Must Work on Day 1)

| # | Use Case | Tools Required | Test |
|---|----------|---------------|------|
| 1 | **"What do you remember about me?"** | LearningMachine | Tell agent facts → new session → ask what it remembers |
| 2 | **"Search the web for X"** | DuckDuckGoTools | Search query → verify results |
| 3 | **"Run this command on my server"** | ShellTools | `ls`, `df -h`, `docker ps` via Telegram |
| 4 | **Persona customization** | SOUL.md loader | Custom persona → verify behavior changes |

### Tier 1: Scheduled Automations (Key Differentiator)

| # | Use Case | Tools Required | Test |
|---|----------|---------------|------|
| 5 | **Morning briefing bot** | SchedulerTools + DuckDuckGoTools | Cron at 8am → web search → summarize → deliver to Telegram |
| 6 | **GitHub repo watcher** | SchedulerTools + ShellTools (gh CLI) | Every 6h → check new issues/PRs → alert |
| 7 | **Daily standup prep** | SchedulerTools + ShellTools | Weekdays 8:45am → git log → draft standup → Slack |

### Tier 2: Advanced Workflows

| # | Use Case | Tools Required | Test |
|---|----------|---------------|------|
| 8 | **Website change monitor** | SchedulerTools + Crawl4aiTools | Every 1h → fetch URL → hash → alert on change |
| 9 | **Code execution in sandbox** | E2BTools | "Write and run a script that..." → sandboxed execution |
| 10 | **Research paper finder** | ExaTools + LearningMachine | Search arxiv → summarize → save to memory |
| 11 | **Image generation** | DalleTools or FalTools | "Generate an image of..." → return image |
| 12 | **Self-improving skills** | LearningMachine (LearnedKnowledge) | Complex multi-tool task → verify learning saved → verify recall |

---

## 10. Directory Structure

```
agno-universal-agent/
    README.md                     # Setup guide, use cases, configuration
    SOUL.md                       # Default persona (user-editable)
    config.yaml                   # AgentOS config (quick prompts, etc.)

    # --- Core ---
    agent.py                      # Main agent definition (agent_factory)
    db.py                         # Database + Knowledge base factory (ChromaDb default)
    learning.py                   # LearningMachine configuration (5 stores)
    tools.py                      # Tool assembly with risk tiers (Safe/Productivity/Privileged)
    hooks.py                      # Autonomous skill extraction post-hook
    persona.py                    # SOUL.md loader utility
    identity.py                   # Cross-platform user identity resolver (NEW)
    sessions.py                   # Session linker: canonical user_id → shared session (NEW)
    delivery.py                   # Scheduled task delivery helper (NEW — auto-injects messaging target into cron prompts)

    # --- Entrypoints ---
    run.py                        # AgentOS server (multi-interface)
    cli.py                        # Standalone CLI mode (no server needed)

    # --- Testing ---
    tests/
        test_memory.py            # Memory persistence across sessions
        test_tools.py             # Each tool works correctly
        test_scheduling.py        # Cron job creation and execution
        test_learning.py          # Skill extraction and recall
        test_cross_platform.py    # Same session across interfaces
        test_use_cases.py         # All 12 use cases end-to-end

    # --- Documentation ---
    docs/
        ARCHITECTURE.md           # Design decisions and rationale
        TOOLS.md                  # Available tools and configuration
        USE_CASES.md              # Detailed walkthrough for each use case
        DEPLOYMENT.md             # VPS, Docker, local deployment guides
```

---

## 11. Configuration

### Environment Variables

```bash
# Required (at least one model provider)
OPENAI_API_KEY=sk-...              # Primary model

# Recommended (fallback + better experience)
ANTHROPIC_API_KEY=sk-ant-...       # Fallback model
EXA_API_KEY=...                    # Semantic search
E2B_API_KEY=...                    # Code sandbox

# Optional (per feature)
FIRECRAWL_API_KEY=...              # Premium web scraping
FAL_KEY=...                        # FLUX image generation
ELEVEN_API_KEY=...                 # Text-to-speech
GITHUB_TOKEN=...                   # GitHub operations
OPENWEATHER_API_KEY=...            # Weather data

# Platform tokens (for messaging interfaces)
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
TELEGRAM_BOT_TOKEN=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...

# Database (optional — defaults to SQLite for zero-config)
DATABASE_URL=postgresql+psycopg://ai:ai@localhost:5532/ai
UNIVERSAL_AGENT_DB_MODE=sqlite     # or "postgres"

# Persona (optional)
UNIVERSAL_AGENT_SOUL_PATH=./SOUL.md
UNIVERSAL_AGENT_USER=local-user    # CLI user identity
```

### Zero-Config Start

```bash
# Just this works:
export OPENAI_API_KEY=sk-...
python cli.py
```

SQLite auto-created, default SOUL.md used, core tools loaded, memory enabled.

---

## 12. Testing Strategy

### Unit Tests

| Test | What It Verifies |
|------|------------------|
| `test_persona_loading` | SOUL.md loads correctly, custom path works |
| `test_tool_assembly` | Core tools loaded, optional tools conditional on env vars |
| `test_session_id_derivation` | Same user → same session_id across platforms |
| `test_learning_config` | All 5 stores initialized with correct modes |

### Integration Tests

| Test | What It Verifies |
|------|------------------|
| `test_web_search` | DuckDuckGoTools returns results for a query |
| `test_shell_command` | ShellTools executes `echo hello` and returns output |
| `test_file_operations` | FileTools read/write/search in temp directory |
| `test_memory_persistence` | Save fact → new agent instance → recall fact |
| `test_skill_extraction` | Multi-tool response → post_hook saves learning |
| `test_skill_recall` | Saved learning → new session → semantic search finds it |

### E2E Tests (Require API Keys)

| Test | What It Verifies |
|------|------------------|
| `test_morning_briefing` | Scheduler creates cron → agent runs → web search → formatted output |
| `test_github_watcher` | Scheduler creates cron → gh CLI → new issues detected |
| `test_cross_platform_memory` | Save via CLI → recall via API (simulating Telegram) |
| `test_fallback_on_error` | Primary model fails → fallback model handles it |

---

## 13. Scope Boundaries (What NOT to Build)

| Feature | Why Not |
|---------|---------|
| **CLI TUI with rich UI** | We're building an agent, not a terminal app. `cli.py` uses `agent.cli_app()` |
| **Browser automation** | Complex, requires headless Chrome. Users add via MCP if needed |
| **RL training pipeline** | Different product. Agno doesn't do model fine-tuning |
| **Skills marketplace** | Agno uses vector-embedded learnings, not file-based skills |
| **Plugin system** | Agno's Toolkit system already handles extensibility |
| **19 messaging platforms** | Start with 4 (Slack, Telegram, WhatsApp, AGUI). Add more later |
| **Skin/theme system** | CLI product feature, not relevant for framework demo |
| **Model metadata registry** | Agno handles model capabilities per-provider |
| **Prompt injection scanning** | Should be in Agno core, not this cookbook |
| **Output redaction** | Should be in Agno core, not this cookbook |
| **ACP protocol** | Agno has MCP server mode instead |
| **Profile isolation** | Agno has multi-tenant via user_id + RBAC |

---

## 14. Resolved Design Decisions (Post-Verification)

### Decision 1: Default model → `gpt-4o-mini`
Cheapest viable option for zero-config. Users upgrade via env var or config.

### Decision 2: Vector DB → ChromaDb (zero-config)
**Verified:** ChromaDb works with local file persistence, no server needed. Already used in `cookbook/08_learning/00_quickstart/03_learned_knowledge.py`. LanceDb is an alternative. PgVector for production (requires Docker).

```python
# Zero-config vector DB setup
knowledge = Knowledge(
    vector_db=ChromaDb(
        name="learnings",
        path="tmp/chromadb",
        persistent_client=True,
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)
```

### Decision 3: Tool loading → Core 5 always, rest conditional on env vars
Safe defaults for all interfaces. Privileged tools (Shell, E2B) only on trusted interfaces.

### Decision 4: Scheduled task delivery → AGENT MUST SELF-DELIVER (Critical Finding)

**VERIFIED:** The Agno scheduler does NOT automatically deliver results to messaging platforms. When a cron job fires:
1. Executor POSTs to `/agents/{id}/runs` with `background=true`
2. Polls until completion
3. Stores result in `schedule_runs` table
4. **DOES NOT send to Telegram/Slack/WhatsApp**

**Solution:** The cron prompt must include explicit delivery instructions:
```
"Search for today's top AI news, summarize in 5 bullet points, 
 then use the send_message tool to post the summary to Telegram chat ID {chat_id}"
```

This means:
- The agent needs `TelegramTools` or `SlackTools` in its toolkit
- Cron prompts must be self-contained with delivery target
- The `create_schedule()` helper should auto-inject delivery instructions based on the user's preferred platform

This is a **design module** we need to build: `delivery.py` — wraps schedule creation to auto-append delivery instructions.

---

## 15. Success Criteria

The spec is complete when:
- [ ] All 12 use cases work end-to-end
- [ ] Memory persists across sessions (CLI → restart → recall)
- [ ] Cross-platform continuity works (CLI session = Telegram session)
- [ ] Autonomous skill extraction saves at least one learning
- [ ] Saved learning is recalled in a future session
- [ ] Cron job executes and delivers results to messaging platform
- [ ] Fallback model activates on primary model failure
- [ ] Context compression kicks in on long conversations
- [ ] Zero-config start works (just OPENAI_API_KEY)
- [ ] Custom SOUL.md changes agent behavior

---

## Appendix A: Hermes Feature Parity Matrix

| Hermes Feature | Universal Agent | How |
|---|---|---|
| ONE agent, ALL tools | Single agent, configurable tools | `tools.py` assembly |
| SOUL.md persona | SOUL.md loader | `persona.py` |
| MEMORY.md + USER.md | LearningMachine (UserProfile + UserMemory) | Better: DB-backed, semantic search |
| FTS5 session search | SessionContext store | Better: structured, per-session |
| Autonomous skills | post_hook + LearnedKnowledge | Better: vector search, not grep |
| Cron scheduling | SchedulerTools + AgentOS scheduler | Same capability |
| Multi-platform gateway | AgentOS interfaces | Same capability |
| Cross-platform sessions | Deterministic session_id | Same capability |
| Context compression | CompressionManager | Same capability |
| Error recovery | FallbackConfig | Better: per-error-type routing |
| Terminal execution | ShellTools | Simpler but sufficient |
| Code sandbox | E2BTools | Better: cloud-isolated |
| Web search | DuckDuckGoTools | Same |
| Image generation | DalleTools / FalTools | Same |
| Model switching | Not needed (FallbackConfig handles it) | Different approach |
| 19 messaging platforms | 4 platforms (Slack, Telegram, WhatsApp, AGUI) | Fewer but sufficient |
| Plugin system | Toolkit system (native) | Better: first-class |
| RL training | Not included | Different product |
| Browser automation | Not included | Add via MCP |
| Smart model routing | Not included (v2 feature) | Possible enhancement |
| Prompt caching | Not included (v2 feature) | Possible enhancement |

---

*This spec was produced from a 33-agent analysis of NousResearch/hermes-agent (779 Python files, 42MB), live side-by-side testing, community research across Reddit/X/GitHub, and Codex design review.*
