# AI Employee Vault - Cleanup Script
# Run this to archive debug/test files and delete unnecessary files
#
# Usage: .\scripts\cleanup_project.ps1

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "AI Employee Vault - Project Cleanup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$root\..\.git") {
    $root = "$root\.."
}

Write-Host "Root directory: $root" -ForegroundColor Yellow
Write-Host ""

# Create archive folder
$archivePath = Join-Path $root "_archive"
if (-not (Test-Path $archivePath)) {
    New-Item -ItemType Directory -Path $archivePath -Force | Out-Null
    Write-Host "[OK] Created archive folder: $archivePath" -ForegroundColor Green
}

# Files to archive (debug/test files that might be useful later)
$archiveFiles = @(
    "scripts\debug_mcp.py",
    "scripts\debug_mcp_detailed.py",
    "scripts\debug_navigate_response.py",
    "scripts\debug_navigate_session.py",
    "scripts\debug_session_detailed.py",
    "scripts\verify_debug.py",
    "scripts\minimal_repro.py",
    "scripts\gmasender_debug.py",
    "scripts\test_session_change.py",
    "scripts\test_session_headers.py",
    "scripts\test_notification.py",
    "scripts\test_no_notification.py",
    "scripts\test_keepalive.py",
    "scripts\test_multiple_calls.py",
    "scripts\test_endpoints.py",
    "scripts\test_different_urls.py",
    "scripts\test_gmail_flow.py",
    "scripts\PLAYWRIGHT_MCP_FIX_COMPLETE.md",
    "scripts\README_MCP_FIX.md"
)

Write-Host "Archiving debug/test files..." -ForegroundColor Yellow
$archived = 0
foreach ($file in $archiveFiles) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
        $dst = Join-Path $archivePath (Split-Path -Leaf $file)
        Move-Item $src -Destination $dst -Force
        Write-Host "  Archived: $file" -ForegroundColor Gray
        $archived++
    }
}
Write-Host "[OK] Archived $archived files" -ForegroundColor Green
Write-Host ""

# Files to delete (unnecessary)
$deleteFiles = @(
    "`$null",
    ".gmail_processed.json"
)

Write-Host "Deleting unnecessary files..." -ForegroundColor Yellow
$deleted = 0
foreach ($file in $deleteFiles) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
        Remove-Item $src -Force
        Write-Host "  Deleted: $file" -ForegroundColor Gray
        $deleted++
    }
}

# Also check root for duplicate test files
$rootTestFiles = @("test_gmail_nav.py", "test_email_send.py")
foreach ($file in $rootTestFiles) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
        Remove-Item $src -Force
        Write-Host "  Deleted: $file" -ForegroundColor Gray
        $deleted++
    }
}

Write-Host "[OK] Deleted $deleted files" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "CLEANUP SUMMARY" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Files archived: $archived" -ForegroundColor White
Write-Host "  Files deleted:  $deleted" -ForegroundColor White
Write-Host ""
Write-Host "Archive location: $archivePath" -ForegroundColor Yellow
Write-Host ""
Write-Host "You can safely delete the _archive folder anytime." -ForegroundColor Gray
Write-Host "==================================================" -ForegroundColor Cyan
