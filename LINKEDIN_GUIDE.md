# LinkedIn Watcher & Poster - Complete Guide

## Quick Start

### 1. Setup LinkedIn Session (First Time Only)

```bash
python scripts/setup_linkedin.py
```

**What happens:**
- Browser opens with LinkedIn
- You log in normally
- Wait for feed to load
- Close browser
- Session saved to `.linkedin_session/`

### 2. Test the Watcher

```bash
python scripts/linkedin_watcher.py . --once --visible
```

### 3. Start Continuous Monitoring

```bash
python scripts/linkedin_watcher.py .
```

---

## Two Approaches

### Approach 1: Automated Monitoring (Watcher)

The watcher **monitors** LinkedIn for business opportunities:

| Feature | Details |
|---------|---------|
| **What it does** | Checks LinkedIn feed every 5 minutes |
| **Detects** | Keywords: hiring, project, freelance, consulting, contract, collaboration, partnership, client, lead, business |
| **Output** | Creates `.md` files in `/Needs_Action/` folder |
| **Session** | Uses saved cookies in `.linkedin_session/` |

**Commands:**
```bash
# Start monitoring (headless)
python scripts/linkedin_watcher.py .

# Start monitoring (visible - for debugging)
python scripts/linkedin_watcher.py . --visible

# Check once and exit
python scripts/linkedin_watcher.py . --once

# Custom interval (60 seconds)
python scripts/linkedin_watcher.py . -i 60
```

**Example Output:**
```
LinkedIn Watcher - Silver Tier
========================================
Vault: G:\...\AI_Employee_Vault
Interval: 300s
Mode: Headless

Watching LinkedIn. Press Ctrl+C to stop.

2026-02-28 15:30:00 - INFO - Navigating to LinkedIn...
2026-02-28 15:30:15 - INFO - Found 2 relevant LinkedIn items
2026-02-28 15:30:15 - INFO - Created action file: LINKEDIN_job_posting_20260228_153015.md
```

---

### Approach 2: Manual Posting (Simple Poster)

The simple poster helps you **post content** to LinkedIn manually:

| Feature | Details |
|---------|---------|
| **What it does** | Opens LinkedIn, displays content for you to copy/paste |
| **Best for** | Posting approved content with human oversight |
| **Session** | Uses same `.linkedin_session/` folder |

**Commands:**
```bash
# Post custom content
python scripts/simple_linkedin_poster.py --vault . --content "Excited to share our new AI automation service! #AI #Automation"

# Post from approved file
python scripts/simple_linkedin_poster.py --vault . --file Approved/LINKEDIN_POST_20260228.md

# Just open LinkedIn (no content)
python scripts/simple_linkedin_poster.py --vault . --open-only
```

**What happens:**
1. Browser opens with LinkedIn
2. Post content displayed in terminal
3. You click "Start a post"
4. Copy content from terminal (Ctrl+C)
5. Paste into LinkedIn composer (Ctrl+V)
6. You click "Post" when ready

---

## Folder Structure

```
AI_Employee_Vault/
├── scripts/
│   ├── linkedin_watcher.py        # Automated monitoring
│   ├── simple_linkedin_poster.py  # Manual posting helper
│   └── setup_linkedin.py          # Session setup
├── .linkedin_session/             # Browser cookies (auto-created)
├── Needs_Action/                  # Detected opportunities
│   └── LINKEDIN_job_posting_20260228_153015.md
├── Pending_Approval/              # Draft posts awaiting approval
│   └── LINKEDIN_POST_20260228_100000.md
├── Approved/                      # Posts ready to publish
├── Done/                          # Completed posts
└── Logs/
    └── linkedin_20260228.json     # Activity logs
```

---

## Action File Format

When the watcher detects a relevant post:

```markdown
---
type: linkedin
subtype: job_posting
received: 2026-02-28T15:30:15
priority: high
keywords: ["hiring", "project"]
status: pending
---

# LinkedIn Job_posting

## Details
- **Type:** job_posting
- **Priority:** high
- **Keywords:** hiring, project

## Content
[Post text from LinkedIn]

## Suggested Actions
- [ ] Review notification on LinkedIn
- [ ] Determine if action needed
- [ ] Respond or engage if appropriate
- [ ] Log business opportunity if relevant

## Links
- [View on LinkedIn](https://www.linkedin.com/notifications/)
```

---

## Troubleshooting

### "Not logged in to LinkedIn"

**Solution:** Re-run setup
```bash
python scripts/setup_linkedin.py
```

### Session keeps expiring

**Cause:** LinkedIn clears cookies frequently

**Solution:** Use visible mode to keep session alive longer:
```bash
python scripts/linkedin_watcher.py . --visible
```

Or manually log in before running:
```bash
python scripts/simple_linkedin_poster.py --vault . --open-only
# Leave browser open, then run watcher in another terminal
python scripts/linkedin_watcher.py .
```

### "Feed page didn't load"

**Cause:** LinkedIn's selectors changed or page slow to load

**Solution:** The updated script already has better fallback selectors. If still failing:
1. Run with `--visible` to see what's happening
2. Check if LinkedIn requires captcha/verification
3. Manually verify you can access LinkedIn in regular browser

### No items detected

**Check:**
1. Is your feed actually showing posts with keywords?
2. Check `Logs/linkedin_*.json` for details
3. Run with `--visible` to debug

---

## Workflow Examples

### Daily Monitoring Workflow

```bash
# Morning: Start watcher
python scripts/linkedin_watcher.py .

# Throughout day: Check Needs_Action folder
# Process any new action files manually or with Qwen Code

# Evening: Stop watcher (Ctrl+C)
```

### Posting Workflow

```bash
# 1. Create draft in Pending_Approval
# (Manually or via automation)

# 2. Review and move to Approved
mv Pending_Approval/LINKEDIN_POST_*.md Approved/

# 3. Post content
python scripts/simple_linkedin_poster.py --vault . --file Approved/LINKEDIN_POST_*.md

# 4. File auto-moves to Done after posting
```

---

## Advanced: Using with Your Browser

If you want to use your **existing Chrome profile** (with saved LinkedIn login):

```python
# Modify the script to use your profile:
browser = p.chromium.launch_persistent_context(
    "C:\\Users\\YOUR_NAME\\AppData\\Local\\Google\\Chrome\\User Data",
    headless=False,
    channel='chrome'
)
```

**Warning:** This can interfere with your regular browsing. Better to use the dedicated session.

---

## API Reference

### LinkedInWatcher

```python
from scripts.linkedin_watcher import LinkedInWatcher

watcher = LinkedInWatcher(
    vault_path=".",
    check_interval=300,  # 5 minutes
    headless=True
)

# Check once
items = watcher.check_for_updates()

# Create action file
for item in items:
    watcher.create_action_file(item)

# Run continuously (blocks)
watcher.run()
```

### SimpleLinkedInPoster

```python
from scripts.simple_linkedin_poster import SimpleLinkedInPoster

poster = SimpleLinkedInPoster(vault_path=".")

# Post content
poster.post("Your post content here")

# Post from file
from pathlib import Path
poster.post_from_file(Path("Approved/LINKEDIN_POST.md"))
```

---

## Tips

1. **Run watcher in visible mode** initially to verify it's working
2. **Check logs regularly** in `Logs/` folder
3. **Clear old processed items** if `.linkedin_processed.json` gets large
4. **Use approval workflow** for important posts
5. **Test with `--once`** before running continuously

---

## Resources

- [Playwright Documentation](https://playwright.dev/python/docs/intro)
- [LinkedIn Brand Guidelines](https://brand.linkedin.com/policies)
- [Best Posting Times](https://www.linkedin.com/business/talent/blog/talent-acquisition/best-times-to-post-on-linkedin)

---

*Created for AI Employee Vault - Silver Tier*
