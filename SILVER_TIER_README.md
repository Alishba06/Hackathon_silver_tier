# AI Employee - Silver Tier

**Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.**

This is the **Silver Tier** implementation of the Personal AI Employee hackathon, featuring Gmail and LinkedIn watchers that automatically monitor communications and create actionable tasks for Qwen Code to process.

## Silver Tier Features

✅ **Gmail Watcher** - Monitors Gmail for unread emails, creates action files  
✅ **LinkedIn Watcher** - Monitors LinkedIn for opportunities and notifications  
✅ **File System Watcher** - Watches drop folder for new files  
✅ **Orchestrator** - Coordinates task processing with Qwen Code  
✅ **Human-in-the-Loop** - Approval workflow for sensitive actions  
✅ **Automated Posting** - LinkedIn auto-posting with approval  

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Employee - Silver Tier                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Gmail API     │  │   LinkedIn      │  │   File System   │
│   (Emails)      │  │   (Opportunities)│  │   (Drops)       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    WATCHERS (Python)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Gmail        │  │ LinkedIn     │  │ File         │      │
│  │ Watcher      │  │ Watcher      │  │ Watcher      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼────────────────┼────────────────┼────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    OBSIDIAN VAULT                           │
│  /Needs_Action/  /Plans/  /Pending_Approval/  /Approved/   │
│  Dashboard.md  Company_Handbook.md  Business_Goals.md       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    QWEN CODE (Brain)                        │
│         Reads tasks, reasons, creates plans, executes       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Verify Setup

```bash
python scripts/verify_silver_tier.py .
```

### 3. Authenticate Gmail

```bash
python scripts/gmail_watcher.py . --auth
```

This will open a browser for OAuth authentication. Complete the flow and the token will be saved.

### 4. Setup LinkedIn Session

```bash
python scripts/linkedin_watcher.py . --setup
```

Log in to LinkedIn manually in the browser that opens, then close it when your feed loads.

### 5. Start All Watchers

```bash
python scripts/start_all_watchers.py .
```

## Watcher Details

### Gmail Watcher

**What it does:**
- Checks Gmail every 120 seconds for unread emails
- Detects priority keywords (urgent, invoice, payment, etc.)
- Creates action files in `/Needs_Action/`
- Tracks processed emails to avoid duplicates

**Action File Format:**
```markdown
---
type: email
from: sender@example.com
subject: Invoice #1234
received: 2026-02-27T10:30:00Z
priority: high
---

# Email: Invoice #1234

## Content
[Email snippet]

## Suggested Actions
- [ ] Read full email
- [ ] Draft reply
- [ ] Archive
```

**Commands:**
```bash
# Authenticate (first time only)
python scripts/gmail_watcher.py . --auth

# Start watching
python scripts/gmail_watcher.py .

# Check once (not continuous)
python scripts/gmail_watcher.py . --once

# Custom interval
python scripts/gmail_watcher.py . -i 60
```

### LinkedIn Watcher

**What it does:**
- Checks LinkedIn every 300 seconds
- Monitors notifications for business opportunities
- Detects keywords (hiring, project, consulting, etc.)
- Creates action files for relevant items

**Commands:**
```bash
# Setup session (first time only)
python scripts/linkedin_watcher.py . --setup

# Start watching
python scripts/linkedin_watcher.py .

# Check once
python scripts/linkedin_watcher.py . --once

# Visible mode (for debugging)
python scripts/linkedin_watcher.py . --visible
```

### File System Watcher

**What it does:**
- Monitors `/Files/Incoming/` folder
- Detects new files automatically
- Creates metadata and action files

**Commands:**
```bash
python scripts/filesystem_watcher.py .
```

### Orchestrator

**What it does:**
- Watches `/Needs_Action/` for new items
- Calls Qwen Code to analyze and route items
- Moves files to appropriate folders
- Updates Dashboard.md

**Commands:**
```bash
# Run continuously
python scripts/orchestrator.py . watch

# Run one cycle
python scripts/orchestrator.py . run

# Check status
python scripts/orchestrator.py . status
```

## Folder Structure

```
AI_Employee_Vault/
├── scripts/
│   ├── gmail_watcher.py          # Gmail monitoring
│   ├── linkedin_watcher.py       # LinkedIn monitoring
│   ├── filesystem_watcher.py     # File drop monitoring
│   ├── orchestrator.py           # Task orchestration
│   ├── start_all_watchers.py     # Unified launcher
│   └── verify_silver_tier.py     # Setup verification
├── Inbox/                        # Raw incoming items
├── Needs_Action/                 # Items requiring attention
├── Plans/                        # Multi-step task plans
├── Pending_Approval/             # Awaiting human approval
├── Approved/                     # Approved actions
├── Rejected/                     # Rejected actions
├── Done/                         # Completed tasks
├── Files/Incoming/               # Drop folder for files
├── Logs/                         # Activity logs
├── credentials.json              # Gmail OAuth (you have this)
├── token.json                    # Gmail OAuth token (created)
├── Dashboard.md                  # Real-time status
├── Business_Goals.md             # Q1/Q2 objectives
└── Company_Handbook.md           # Rules of engagement
```

## Human-in-the-Loop Workflow

For sensitive actions (payments, posting to social media, emails to new contacts):

1. **Watcher/Orchestrator** creates approval request in `/Pending_Approval/`
2. **You** review the request
3. **You** move file to `/Approved/` to approve or `/Rejected/` to decline
4. **Orchestrator** executes approved actions

**Example Approval Request:**
```markdown
---
type: approval_request
action: linkedin_post
content_preview: Excited to announce...
created: 2026-02-27T10:00:00Z
---

# LinkedIn Post - Approval Required

## Content
Excited to announce our new AI automation service!

## To Approve
Move to `/Approved` to post.

## To Reject
Move to `/Rejected` with reason.
```

## Integration with Qwen Code

The Orchestrator automatically calls Qwen Code to:
1. Analyze incoming items
2. Determine routing (Done, Plans, Pending Approval)
3. Execute tasks based on Company Handbook rules
4. Create plans for complex multi-step tasks

**Example Qwen Code Prompt:**
```
You are an AI Employee workflow assistant. Analyze this action item and 
determine where it should be routed...

[Item content]

Return ONLY a JSON object with routing decision.
```

## Monitoring & Logs

All activity is logged to `/Logs/`:

```
Logs/
├── gmail_20260227.json           # Gmail activity
├── linkedin_20260227.json        # LinkedIn activity
├── orchestrator_20260227.jsonl   # Orchestration decisions
└── scheduler.log                 # Scheduled tasks
```

## Troubleshooting

### Gmail Watcher Issues

**"Authentication failed"**
```bash
# Re-run authentication
python scripts/gmail_watcher.py . --auth
```

**"Token expired"**
```bash
# Delete old token and re-authenticate
rm token.json
python scripts/gmail_watcher.py . --auth
```

### LinkedIn Watcher Issues

**"Not logged in"**
```bash
# Re-setup session
python scripts/linkedin_watcher.py . --setup
```

**"Browser won't close"**
```bash
# Kill stuck processes
taskkill /F /IM python*
```

### General Issues

**Verify setup:**
```bash
python scripts/verify_silver_tier.py .
```

**Check logs:**
```bash
# View recent logs
tail Logs/orchestrator_*.jsonl
```

## Silver Tier Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Playwright browsers installed (`playwright install chromium`)
- [ ] Gmail credentials.json exists
- [ ] Gmail OAuth completed (`--auth`)
- [ ] LinkedIn session created (`--setup`)
- [ ] All watchers start successfully
- [ ] Action files created in Needs_Action/
- [ ] Qwen Code processes items
- [ ] Approval workflow works

## Next Steps (Gold Tier)

To upgrade to Gold Tier:
- Add WhatsApp monitoring
- Integrate Odoo accounting
- Add Facebook/Instagram posting
- Implement weekly CEO briefings
- Add error recovery and audit logging

## Resources

- [Hackathon Document](Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md)
- [Qwen Code Documentation](https://platform.claude.com/docs)
- [Gmail API Setup](https://developers.google.com/gmail/api/quickstart/python)
- [Playwright Documentation](https://playwright.dev/python/docs/intro)

---

*AI Employee v0.2 (Silver Tier) - Built for Panaversity Hackathon 0*
