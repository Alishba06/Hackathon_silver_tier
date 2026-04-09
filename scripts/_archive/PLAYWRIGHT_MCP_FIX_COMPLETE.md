# Playwright MCP Session Fix - COMPLETE

## Problem Solved ✅

The original issue was:
```
[1] Navigating to Gmail...
[INIT] Session created: 08102213-eb64-4514-806e-4a1b72106ce2
[TOOL] Calling browser_navigate
Result: OK

[3] Taking snapshot...
[TOOL] Calling browser_snapshot
Error: HTTP Error 404: Session not found
```

## Root Cause Analysis

After extensive debugging, I identified **TWO critical issues**:

### Issue 1: Session ID Not Extracted from Error Responses

When the MCP server returns an HTTP error (like 404), it may **still include a session ID** in the response headers. The original code only extracted session IDs from successful responses:

```python
# ❌ ORIGINAL - Only extracts from success responses
try:
    with urlopen(req, timeout=60) as resp:
        new_session = resp.headers.get('Mcp-Session-Id')
        self._session_id = new_session
        body = resp.read().decode('utf-8')
        return self._parse_sse(body)
except HTTPError as e:
    # Session ID in e.headers was IGNORED!
    body = e.read().decode('utf-8')
    return None, f"HTTP {e.code}: {body}"
```

### Issue 2: Transient Server State

The Playwright MCP server can get into a stale state after:
- Browser context is closed
- Multiple rapid requests
- Navigation operations that reset internal state

## The Complete Fix

### Fix 1: Extract Session from Error Responses

```python
# ✅ FIXED - Extract session from BOTH success and error responses
except HTTPError as e:
    # CRITICAL: Extract session ID from error response headers too!
    error_headers = dict(e.headers) if hasattr(e, 'headers') and e.headers else {}
    new_session_id = error_headers.get('Mcp-Session-Id') or error_headers.get('mcp-session-id')
    if new_session_id and new_session_id != self._session_id:
        print(f"    [SESSION] Updated from error response: {self._session_id[:8]}... -> {new_session_id[:8]}...")
        self._session_id = new_session_id
    
    body = e.read().decode('utf-8') if e.fp else str(e)
    # ... handle error
```

### Fix 2: Session Extraction Before Body Consumption

```python
# ✅ CRITICAL: Always extract session ID BEFORE reading body
with urlopen(req, timeout=120) as resp:
    # Get session ID FIRST
    new_session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
    if new_session_id:
        self._session_id = new_session_id
    
    # THEN read body
    body = resp.read().decode('utf-8')
    return self._parse_sse_response(body)
```

### Fix 3: Dual Header Format

```python
# ✅ Send BOTH header formats for maximum compatibility
headers["mcp-session-id"] = self._session_id
headers["Mcp-Session-Id"] = self._session_id
```

## Verification Results

```
[Test 1] Initialize MCP session...
  [PASS] Session ID: 0f2a4a26-063b-442a-a0e6-b4cc1d06409d

[Test 2] Snapshot immediately after initialize...
  [PASS] Snapshot received (58 chars)

[Test 3] Navigate to example.com...
  [PASS] Navigation successful

[Test 4] Snapshot after navigation...
  [PASS] Snapshot received (411 chars)

[Test 5] Multiple consecutive tool calls...
  [OK] Call 1 succeeded
  [OK] Call 2 succeeded
  [OK] Call 3 succeeded
  [PASS] All 3 calls succeeded with same session

[SUCCESS] ALL TESTS PASSED!
```

## Files Created/Updated

| File | Purpose |
|------|---------|
| `gmasender.py` | **Main email sender** - Fixed version with complete session handling |
| `verify_mcp_fix.py` | Verification script to test session persistence |
| `verify_debug.py` | Debug version with extra logging |
| `debug_navigate_session.py` | Low-level session behavior debugger |
| `minimal_repro.py` | Minimal reproduction of verify flow |
| `README_MCP_FIX.md` | Documentation |

## How to Use

### Step 1: Start MCP Server

```bash
npx @playwright/mcp@latest --port 8808
```

Keep this terminal open.

### Step 2: Verify Fix

In a new terminal:

```bash
cd G:\ALISHBA VVC\governor house work\governor-house-quater-4-work\start-hackthons\hackathon_0_part_1\AI_Employee_Vault

python scripts\verify_mcp_fix.py
```

### Step 3: Send Email

```bash
python scripts\gmasender.py "recipient@example.com" "Subject" "Email body"
```

Example:
```bash
python scripts\gmasender.py "test@gmail.com" "Hello" "This is a test email"
```

## Technical Details

### Streamable HTTP Transport

Playwright MCP uses **streamable HTTP transport** (MCP spec v2024-11-05):

1. **Initialize**: First request creates session, returns `Mcp-Session-Id` header
2. **Subsequent Requests**: Include session ID in request headers
3. **Session Updates**: Server may return new session ID in ANY response (including errors)
4. **SSE Format**: Responses use Server-Sent Events

### Key Implementation Pattern

```python
def _send_request(self, payload, include_session=True):
    # Prepare request
    headers = {...}
    if self._session_id:
        headers["mcp-session-id"] = self._session_id
        headers["Mcp-Session-Id"] = self._session_id
    
    req = Request(self.base_url, data=data, headers=headers, method='POST')
    
    try:
        with urlopen(req, timeout=120) as resp:
            # STEP 1: Extract session BEFORE body
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            if new_session:
                self._session_id = new_session
            
            # STEP 2: Read body
            body = resp.read().decode('utf-8')
            return self._parse_sse(body)
            
    except HTTPError as e:
        # STEP 3: Also extract session from error response
        error_headers = dict(e.headers)
        new_session = error_headers.get('Mcp-Session-Id') or error_headers.get('mcp-session-id')
        if new_session:
            self._session_id = new_session
        
        # STEP 4: Handle error
        body = e.read().decode('utf-8')
        # ... error handling
```

## Troubleshooting

### If Tests Still Fail

1. **Restart MCP server** - Clear any stale state:
   ```bash
   # Stop current server (Ctrl+C)
   npx @playwright/mcp@1.0.0 --port 8808
   ```

2. **Reinstall Playwright**:
   ```bash
   npx playwright install --force
   ```

3. **Check server is responding**:
   ```bash
   curl -X POST http://localhost:8808 \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
   ```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection failed` | Server not running | Start MCP server |
| `HTTP 404: Session not found` | Session expired | Script auto-retries, or restart server |
| `Browser context closed` | Browser was closed | Restart MCP server |
| `Login timeout` | Not logged into Gmail | Complete login in browser window |

## Lessons Learned

1. **Always extract session headers before reading body** - HTTP response streams can only be read once
2. **Error responses may contain session updates** - Don't ignore headers on errors
3. **Send both header case variations** - `mcp-session-id` and `Mcp-Session-Id`
4. **Server state can be transient** - Implement automatic reinitialization
5. **Debug with fresh server instances** - Stale state causes intermittent failures

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [Streamable HTTP Transport](https://spec.modelcontextprotocol.io/architecture/2024-11-05/http/)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)

---

*Fix implemented and verified on 2026-03-10*
