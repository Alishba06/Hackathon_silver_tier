# AI Employee Vault - Project Context

## Project Overview

This is a **Personal AI Employee** hackathon project that builds an autonomous "Digital FTE" (Full-Time Equivalent) using **Claude Code** as the reasoning engine and **Obsidian** as the local-first dashboard/memory system.

### Core Concept

The AI Employee operates 24/7 to manage personal and business affairs autonomously:
- **Perception**: Python "Watcher" scripts monitor Gmail, WhatsApp, filesystems, and bank transactions
- **Reasoning**: Claude Code processes tasks from the Obsidian vault
- **Action**: MCP (Model Context Protocol) servers execute external actions (emails, payments, social media)
- **Human-in-the-Loop**: Sensitive actions require approval via file movement (`/Pending_Approval` → `/Approved`)

### Architecture Layers

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Brain** | Claude Code | Reasoning engine, multi-step task planning |
| **Memory/GUI** | Obsidian (Markdown) | Dashboard, long-term memory, state tracking |
| **Senses** | Python Watchers | Monitor Gmail, WhatsApp, filesystems, transactions |
| **Hands** | MCP Servers | External actions (email, browser, payments, social media) |
| **Persistence** | Ralph Wiggum Loop | Keeps Claude working until tasks complete |

## Directory Structure

```
AI_Employee_Vault/
├── .qwen/skills/           # Qwen agent skills (browsing-with-playwright)
├── .claude/                # Claude Code configuration (plugins, MCP)
├── Inbox/                  # Raw incoming items (to be processed)
├── Needs_Action/           # Items requiring attention
├── In_Progress/<agent>/    # Claims by agents (prevents duplicate work)
├── Pending_Approval/       # Actions awaiting human approval
├── Approved/               # Approved actions (triggers execution)
├── Rejected/               # Rejected actions
├── Done/                   # Completed tasks
├── Accounting/             # Bank transactions, financial records
├── Business_Goals.md       # Q1/Q2 objectives, metrics, targets
├── Company_Handbook.md     # Rules of engagement, policies
├── Dashboard.md            # Real-time summary (balance, pending, active)
└── Briefings/              # Generated CEO briefings (weekly audits)
```

## Building & Running

### Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Claude Code | Active subscription | Primary reasoning engine |
| Obsidian | v1.10.6+ | Knowledge base & dashboard |
| Python | 3.13+ | Watcher scripts, orchestration |
| Node.js | v24+ LTS | MCP servers |
| GitHub Desktop | Latest | Version control |

### Setup Commands

```bash
# Verify Claude Code
claude --version

# Start Playwright MCP server (for web automation)
bash .qwen/skills/browsing-with-playwright/scripts/start-server.sh

# Verify Playwright server
python3 .qwen/skills/browsing-with-playwright/scripts/verify.py

# Stop Playwright server (when done)
bash .qwen/skills/browsing-with-playwright/scripts/stop-server.sh
```

### Running the AI Employee

```bash
# Start Ralph Wiggum loop (keeps Claude working until task complete)
/ralph-loop "Process all files in /Needs_Action, move to /Done when complete" \
  --completion-promise "TASK_COMPLETE" \
  --max-iterations 10

# Or trigger via orchestrator
claude "Check /Needs_Action and /Accounting for new items"
```

### Scheduled Operations

| Operation | Trigger | Description |
|-----------|---------|-------------|
| Daily Briefing | 8:00 AM cron/Task Scheduler | Summarize business tasks |
| Weekly Audit | Sunday night | Revenue, bottlenecks, subscription review |
| Continuous | Python watchdog | Monitor WhatsApp/Gmail for urgent keywords |

## Development Conventions

### File Naming Patterns

- `EMAIL_<message_id>.md` - Email action items
- `WHATSAPP_<chat_id>_<timestamp>.md` - WhatsApp messages
- `FILE_<original_name>` - Dropped files for processing
- `PAYMENT_<recipient>_<date>.md` - Payment approval requests
- `YYYY-MM-DD_Monday_Briefing.md` - Generated CEO briefings

### Markdown Schema Standards

All action files use YAML frontmatter:

```yaml
---
type: email|whatsapp|payment|file_drop|approval_request
from: sender@example.com
subject: Invoice #1234
received: 2026-01-07T10:30:00Z
priority: high|medium|low
status: pending|in_progress|approved|rejected|done
---
```

### Agent Skills

All AI functionality should be implemented as **[Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)** - reusable, prompt-driven capabilities that Claude can invoke autonomously.

### Claim-by-Move Rule

To prevent duplicate work in multi-agent setups:
1. First agent to move item from `/Needs_Action` to `/In_Progress/<agent>/` owns it
2. Other agents must ignore items in `/In_Progress/` folders
3. Single-writer rule for `Dashboard.md` (Local agent only)

### Security Rules

- **Secrets never sync**: `.env`, tokens, WhatsApp sessions, banking credentials stay local
- **Cloud owns**: Email triage, draft replies, social post drafts (draft-only)
- **Local owns**: Approvals, WhatsApp session, payments/banking, final send/post actions

## Hackathon Tiers

| Tier | Time | Deliverables |
|------|------|--------------|
| **Bronze** | 8-12 hrs | Obsidian vault, 1 Watcher, basic folder structure |
| **Silver** | 20-30 hrs | 2+ Watchers, MCP server, HITL approval, cron scheduling |
| **Gold** | 40+ hrs | Full integration, Odoo accounting, Ralph Wiggum loop, audit logging |
| **Platinum** | 60+ hrs | Cloud deployment, work-zone specialization, A2A upgrade |

## Key MCP Servers

| Server | Capabilities | Use Case |
|--------|--------------|----------|
| `filesystem` | Read, write, list files | Built-in, vault operations |
| `email-mcp` | Send, draft, search emails | Gmail integration |
| `browser-mcp` | Navigate, click, fill forms | Payment portals, web automation |
| `calendar-mcp` | Create, update events | Scheduling meetings |
| `mcp-odoo-adv` | Odoo JSON-RPC APIs | Accounting, invoices, payments |

## Available Skills

- **browsing-with-playwright**: Browser automation via Playwright MCP (navigate, fill forms, click, screenshots, data extraction)

## Testing & Verification

```bash
# Verify Playwright MCP server
python3 .qwen/skills/browsing-with-playwright/scripts/verify.py

# Expected output: ✓ Playwright MCP server running
```

## Resources

- **Hackathon Document**: `Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md`
- **Playwright Tools Reference**: `.qwen/skills/browsing-with-playwright/references/playwright-tools.md`
- **Ralph Wiggum Plugin**: https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum
- **Agent Skills Docs**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **Wednesday Research Meetings**: Zoom ID 871 8870 7642 (10:00 PM, Jan 7th 2026 start)
