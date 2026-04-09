@echo off
REM ================================================
REM Start Playwright MCP Server
REM ================================================
REM This script starts the Playwright MCP server
REM for browser automation (Gmail, LinkedIn, etc.)
REM
REM Server will run on: http://localhost:8808
REM Press Ctrl+C to stop the server
REM ================================================

echo ========================================================
echo Playwright MCP Server Starter
echo ========================================================
echo.
echo Server URL: http://localhost:8808
echo.
echo IMPORTANT: Keep this window OPEN while using Gmail automation.
echo To stop the server, press Ctrl+C in this window.
echo.
echo Starting server...
echo.

REM Use --shared-browser-context for persistent session
REM --no-sandbox disables sandbox for better stability on Windows
npx @playwright/mcp@latest --port 8808 --shared-browser-context --no-sandbox

echo.
echo Server stopped.
pause
