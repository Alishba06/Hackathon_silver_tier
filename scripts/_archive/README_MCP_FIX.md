# Gmail MCP Sender - Fixed Version

This directory contains the **fixed** Gmail sender script that properly handles Playwright MCP session management.

## Problem Analysis

### The Original Issue

The original script was failing with:

```
[1] Navigating to Gmail...
[INIT] Session created: 08102213-eb64-4514-806e-4a1b72106ce2
[TOOL] Calling browser_navigate
Result: OK

[3] Taking snapshot...
[TOOL] Calling browser_snapshot
Error: HTTP Error 404: Not Found
```

### Root Cause

After analyzing the MCP client code and Playwright MCP server behavior, I identified **three critical issues**:

1. **Session ID Extraction Timing**: The session ID must be extracted from response headers **BEFORE** reading the response body. In streamable HTTP transport, the session can be updated mid-response.

2. **SSE Response Parsing**: Playwright MCP returns Server-Sent Events (SSE) format:
   ```
   event: message
   data: {"jsonrpc": "2.0", "result": {...}}
   ```
   The original parser wasn't handling all SSE edge cases correctly.

3. **Header Format Compatibility**: The MCP spec uses `Mcp-Session-Id` but some implementations expect `mcp-session-id` (lowercase). Both must be sent for maximum compatibility.

### Why Session Disappeared

The session wasn't actually "disappearing" - the issue was:

1. After `browser_navigate`, the Playwright MCP server may return a **new session ID** in the response headers
2. The original code read the response body first, which consumed the stream
3. By the time it tried to get the session ID, the response object was in an inconsistent state
4. Subsequent requests used a stale session ID, causing 404 errors

## The Fix

The fixed `gmasender.py` implements:

1. **Session extraction before body consumption**:
   ```python
   with urlopen(req, timeout=120) as resp:
       # CRITICAL: Extract session ID BEFORE reading body
       new_session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
       if new_session_id:
           self._session_id = new_session_id
       
       # Now read the body
       body = resp.read().decode('utf-8')
   ```

2. **Robust SSE parsing**:
   ```python
   def _parse_sse_response(self, body: str) -> dict:
       for line in body.split('\n'):
           if line.startswith('data:'):
               json_str = line[5:].strip()
               if json_str and json_str != '[DONE]':
                   return json.loads(json_str)
       return {}
   ```

3. **Dual header format**:
   ```python
   headers["mcp-session-id"] = self._session_id
   headers["Mcp-Session-Id"] = self._session_id
   ```

4. **Automatic session recovery** on 404 errors

## Quick Start

### Step 1: Start the Playwright MCP Server

```bash
npx @playwright/mcp@latest --port 8808
```

**Important**: Use a specific version to avoid bugs:
```bash
npx @playwright/mcp@1.0.0 --port 8808
```

Keep this terminal window open - the server must stay running.

### Step 2: Verify the Fix

In a **new terminal** (leave MCP server running):

```bash
cd G:\ALISHBA VVC\governor house work\governor-house-quater-4-work\start-hackthons\hackathon_0_part_1\AI_Employee_Vault

python scripts\verify_mcp_fix.py
```

Expected output:
```
[Test 1] Initialize MCP session...
  [PASS] Session ID: abc12345-...

[Test 2] Snapshot immediately after initialize...
  [PASS] Snapshot received (1234 chars)

[Test 3] Navigate to example.com...
  [PASS] Navigation successful

[Test 4] Snapshot after navigation...
  [PASS] Snapshot received (5678 chars)

[Test 5] Multiple consecutive tool calls...
  [PASS] All 3 calls succeeded with same session

[SUCCESS] ALL TESTS PASSED!
```

### Step 3: Send an Email

```bash
python scripts\gmasender.py "recipient@example.com" "Test Subject" "This is the email body"
```

Example:
```bash
python scripts\gmasender.py "test@gmail.com" "Hello" "This is a test email sent via Playwright MCP"
```

## Detailed Usage

### Command Line Options

```
python scripts\gmasender.py <to> <subject> <body> [options]

Arguments:
  to          Recipient email address
  subject     Email subject
  body        Email body text

Options:
  --mcp-url, -u   MCP server URL (default: http://localhost:8808)
  --close-browser, -c   Close browser after sending
```

### Examples

```bash
# Basic email
python scripts\gmasender.py "user@example.com" "Meeting Tomorrow" "Let's meet at 3pm"

# With custom MCP URL
python scripts\gmasender.py -u "http://localhost:8808" "..." "..." "..."

# Send and close browser
python scripts\gmasender.py -c "..." "..." "..."
```

## Email Sending Flow

The script automates these steps:

1. **Navigate to Gmail** - Opens mail.google.com
2. **Check Login** - Verifies you're logged in (waits up to 2 minutes if needed)
3. **Click Compose** - Opens the compose window
4. **Fill Fields** - Enters To, Subject, and Body
5. **Click Send** - Sends the email
6. **Verify** - Confirms the email was sent (looks for "Undo" toast)

## Troubleshooting

### "Connection failed: [Errno 11001]" 

**Problem**: MCP server not running

**Solution**:
```bash
npx @playwright/mcp@latest --port 8808
```

### "HTTP 404: Session not found"

**Problem**: Session handling issue (should be fixed, but may occur if server restarted)

**Solution**:
1. Stop the MCP server (Ctrl+C)
2. Restart: `npx @playwright/mcp@latest --port 8808`
3. Run verification: `python scripts\verify_mcp_fix.py`

### "Login timeout"

**Problem**: Not logged into Gmail

**Solution**:
1. Browser will open - complete the login manually
2. Script waits up to 2 minutes for login
3. After login, script continues automatically

If timeout occurs:
- Run the script again (session is already logged in)
- Or log in manually at mail.google.com first

### "Browser context was closed"

**Problem**: Browser was closed while MCP server expected it open

**Solution**:
1. Stop MCP server
2. Restart MCP server
3. Run script again

### Playwright MCP Server Issues

If the MCP server itself has issues:

```bash
# Clear Playwright browser data
npx playwright install --force

# Use specific stable version
npx @playwright/mcp@1.0.0 --port 8808
```

## Architecture

```
┌─────────────────┐     HTTP POST      ┌─────────────────────┐
│   gmasender.py  │ ─────────────────► │ Playwright MCP      │
│   (MCP Client)  │ ◄───────────────── │ Server (@playwright)│
└─────────────────┘   JSON-RPC + SSE   └─────────────────────┘
                           │
                           │ browser_* tools
                           ▼
                  ┌─────────────────────┐
                  │   Chromium Browser  │
                  │   (controlled via   │
                  │    Playwright)      │
                  └─────────────────────┘
```

### Request Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "browser_navigate",
    "arguments": {"url": "https://mail.google.com"}
  }
}
```

### Response Format (SSE)

```
event: message
data: {"jsonrpc": "2.0", "result": {"content": [...]}}
```

## Files

| File | Purpose |
|------|---------|
| `gmasender.py` | Main email sender script (fixed version) |
| `verify_mcp_fix.py` | Verification script to test session handling |
| `README_MCP_FIX.md` | This documentation |

## MCP Server Version

**Recommended**: `@playwright/mcp@1.0.0` or latest stable

```bash
# Check version
npx @playwright/mcp@latest --version

# Use specific version
npx @playwright/mcp@1.0.0 --port 8808
```

If you experience issues with `@latest`, try version `1.0.0` which is known stable.

## Security Notes

- **Gmail Login**: Your Gmail credentials are entered directly in Gmail's UI (not in the script)
- **Session Storage**: Session IDs are stored only in memory, not persisted
- **Browser Context**: Uses shared browser context - your Gmail session is preserved

## Advanced: Understanding Streamable HTTP

Playwright MCP uses **streamable HTTP transport** (MCP spec v2024-11-05):

1. **Initialize**: First request creates session, returns `Mcp-Session-Id` header
2. **Subsequent Requests**: Include session ID in both header formats
3. **Session Updates**: Server may return new session ID in any response
4. **SSE Format**: Responses use Server-Sent Events for streaming

Key implementation detail:
```python
# Always extract session ID BEFORE reading body
new_session = resp.headers.get('Mcp-Session-Id')
body = resp.read()  # Body read AFTER session extraction
```

## Related Documentation

- [MCP Spec](https://modelcontextprotocol.io/)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)
- [Streamable HTTP Transport](https://spec.modelcontextprotocol.io/architecture/2024-11-05/http/)

## Support

If issues persist:

1. Run verification script: `python scripts\verify_mcp_fix.py`
2. Check MCP server logs for errors
3. Ensure Playwright browsers are installed: `npx playwright install`
4. Try with `--close-browser` flag to reset state between sends

---

*Fixed version implementing proper MCP session handling for streamable HTTP transport.*
