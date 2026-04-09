---
last_updated: 2026-03-03T14:29:54.013441
status: active
tier: silver
---

# AI Employee Dashboard - Silver Tier

## Quick Status

| Metric | Value |
|--------|-------|
| Pending Items | 0 |
| In Progress | 0 |
| Awaiting Approval | 0 |
| Completed Today | 0 |

## Watcher Status

| Watcher | Status | Last Check |
|---------|--------|------------|
| Gmail | ○ Not running | - |
| LinkedIn | ○ Not running | - |
| File System | ○ Not running | - |
| Orchestrator | ○ Not running | - |

## Bank Balance

> **Current Balance:** $0.00
>
> **Last Updated:** Not yet synced

## Pending Messages

*No pending messages*

## Active Business Projects

*No active projects*

## Recent Activity

| Date | Action | Status |
|------|--------|--------|
| - | - | - |

## Quick Links

### Navigation
- [[Business_Goals]] - Q1/Q2 objectives
- [[Company_Handbook]] - Rules of engagement
- `/Needs_Action/` - Items requiring attention
- `/Pending_Approval/` - Awaiting your approval
- `/Done/` - Completed tasks
- `/Plans/` - Multi-step task plans

### Silver Tier Commands
```bash
# Verify setup
python scripts/verify_silver_tier.py .

# Authenticate Gmail
python scripts/gmail_watcher.py . --auth

# Setup LinkedIn
python scripts/linkedin_watcher.py . --setup

# Start all watchers
python scripts/start_all_watchers.py .

# Start individual watchers
python scripts/gmail_watcher.py .
python scripts/linkedin_watcher.py .
```

---
*AI Employee v0.2 (Silver Tier) - Powered by Qwen Code*
