@echo off
REM Gmail MCP Email Sender - Starts MCP server and sends email
REM Usage: send-email.bat to@example.com "Subject" "Body"

if "%~1"=="" (
    echo Usage: send-email.bat to@example.com "Subject" "Body"
    exit /b 1
)

echo ==================================================
echo Gmail MCP Email Sender
echo ==================================================
echo.
echo Step 1: Starting Playwright MCP server...
echo.

REM Start MCP server in background with persistent browser context
start /B cmd /c "npx @playwright/mcp@latest --port 8808 --shared-browser-context"

echo Waiting for MCP server to start (10 seconds)...
timeout /t 10 /nobreak >nul

echo.
echo Step 2: Sending email...
echo.

REM Run the email sender
python scripts\gmail_mcp_sender.py %*

echo.
echo ==================================================
echo Done! MCP server will close automatically.
echo ==================================================
