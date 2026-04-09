# AI Employee v0.1 - Silver Tier

> **Tagline:** Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.

A Personal AI Employee built with **Claude Code** and **Obsidian** that proactively manages your personal and business affairs 24/7.

## Quick Start

```bash
# 1. Drop a file into the Inbox folder
cp my-document.pdf Inbox/

# 2. Run the orchestrator
python scripts/orchestrator.py . run

# 3. Check the Plans folder for the processing plan
# 4. Check the Dashboard.md for status
```

## What is the AI Employee?

This is a **Digital FTE** (Full-Time Equivalent) - an AI agent that works nearly 9,000 hours/year vs a human's 2,000 hours, at 85-90% cost reduction.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Employee                          │
├─────────────────────────────────────────────────────────┤
│  Perception  →  Reasoning  →  Action                   │
│  (Watchers)     (Claude)     (MCP)                     │
└─────────────────────────────────────────────────────────┘
```

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Perception** | Python Watchers | Monitor Gmail, WhatsApp, filesystems |
| **Reasoning** | Claude Code | Process tasks, create plans |
| **Action** | MCP Servers | Send emails, make payments, post social |
| **Memory** | Obsidian | Dashboard, handbook, goals |

## Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| [Claude Code](https://claude.com/product/claude-code) | Latest | Primary reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge base & dashboard |
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts |
| [Node.js](https://nodejs.org/) | v24+ LTS | MCP servers |

### Install Claude Code

```bash
npm install -g @anthropic/claude-code
claude --version
```

## Folder Structure

```
AI_Employee_Vault/
├── scripts/
│   ├── base_watcher.py       # Base class for all watchers
│   ├── filesystem_watcher.py # Watches Inbox folder
│   └── orchestrator.py       # Main coordinator
├── Inbox/                    # Drop files here
├── Needs_Action/             # Items requiring attention
├── Plans/                    # Claude's processing plans
├── Pending_Approval/         # Awaiting your approval
├── Approved/                 # Approved actions (ready to execute)
├── Done/                     # Completed tasks
├── Accounting/               # Financial records
├── Briefings/                # CEO briefings
├── Logs/                     # Activity logs
├── Dashboard.md              # Real-time status
├── Company_Handbook.md       # Rules of engagement
└── Business_Goals.md         # Objectives & metrics
```

## Usage

### Method 1: File Drop (Simplest)

1. **Drop a file** into the `Inbox/` folder
2. **Run the watcher** (optional - auto-detects in continuous mode)
3. **Run the orchestrator** to process

```bash
# Drop a file
cp invoice.pdf Inbox/

# Run one cycle
python scripts/orchestrator.py . run

# Or run continuously
python scripts/orchestrator.py . watch
```

### Method 2: Direct Claude Code

```bash
# Process all pending items
claude "Check Needs_Action folder and process all pending items"
```

### Running the Filesystem Watcher

```bash
# Start the watcher (monitors Inbox folder)
python scripts/filesystem_watcher.py .

# Watcher will:
# - Detect new files in Inbox/
# - Copy to Needs_Action/
# - Create metadata .md file
```

### Running the Orchestrator

```bash
# Run one cycle
python scripts/orchestrator.py . run

# Run continuously (checks every 60 seconds)
python scripts/orchestrator.py . watch

# Check status
python scripts/orchestrator.py . status
```

## Bronze Tier Deliverables

✅ **Completed:**

- [x] Obsidian vault with Dashboard.md and Company_Handbook.md
- [x] File System Watcher script (watches Inbox folder)
- [x] Claude Code integration (reads/writes to vault)
- [x] Basic folder structure: /Inbox, /Needs_Action, /Done
- [x] Orchestrator for coordinating tasks

## Example Workflow

### Processing a Dropped File

1. **User drops file:** `invoice.pdf` → `Inbox/`
2. **Filesystem Watcher detects:** Creates `FILE_invoice.pdf.meta.md` in `Needs_Action/`
3. **Orchestrator triggers Claude:** Reads the metadata file
4. **Claude creates plan:** `Plans/PLAN_invoice_*.md`
5. **Claude processes:** Determines action needed
6. **If approval needed:** Creates file in `Pending_Approval/`
7. **User approves:** Move file to `Approved/`
8. **Orchestrator executes:** Moves to `Done/`

### Sample Action File

```markdown
---
type: file_drop
original_name: invoice.pdf
size: 245760
received: 2026-02-25T10:30:00
status: pending
source: Inbox
---

# File Dropped for Processing

**Original Name:** invoice.pdf

**Size:** 240.00 KB

**Location:** `FILE_invoice.pdf`

## Suggested Actions

- [ ] Review file contents
- [ ] Process or take action
- [ ] Move to /Done when complete
```

## Configuration

### Company Handbook

Edit `Company_Handbook.md` to customize:

- Communication style
- Financial approval thresholds
- Email handling rules
- Task prioritization

### Business Goals

Edit `Business_Goals.md` to set:

- Revenue targets
- Key metrics
- Active projects
- Subscription tracking

## Troubleshooting

### Claude Code Not Found

```bash
# Install Claude Code
npm install -g @anthropic/claude-code

# Verify installation
claude --version
```

### Watcher Not Detecting Files

```bash
# Check if watchdog is installed (optional, for real-time monitoring)
pip install watchdog

# Or use polling mode (built-in fallback)
python scripts/filesystem_watcher.py .
```

### Permission Errors on Windows

Run as Administrator or adjust folder permissions:

```bash
# Ensure you have write access to the vault
icacls . /grant %USERNAME%:F /T
```

## Next Steps (Silver Tier)

To upgrade to Silver tier:

1. Add Gmail Watcher (monitor inbox)
2. Add WhatsApp Watcher (via Playwright)
3. Implement MCP server for email sending
4. Add cron/Task Scheduler integration
5. Create Plan.md reasoning loop

## Security Notes

⚠️ **Important Security Practices:**

- Never commit `.env` files with credentials
- Use environment variables for API keys
- Review all actions in `Pending_Approval/` before approving
- Regularly audit the `Logs/` folder

## Resources

- [Hackathon Document](./Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md)
- [Claude Code Docs](https://platform.claude.com/docs/)
- [Obsidian Help](https://help.obsidian.md/)
- [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

## License

This project is part of the Personal AI Employee Hackathon 0.

---

*Built with ❤️ using Claude Code + Obsidian*
