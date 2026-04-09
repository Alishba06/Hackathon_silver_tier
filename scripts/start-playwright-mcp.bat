@echo off
REM Start Playwright MCP Server for Gmail automation
REM Server will run at http://localhost:8808

echo Starting Playwright MCP Server...
echo Server URL: http://localhost:8808
echo Press Ctrl+C to stop the server
echo.

npx @playwright/mcp@latest --port 8808 --shared-browser-context
