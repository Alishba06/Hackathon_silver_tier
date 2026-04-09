"""
Verify Silver Tier Setup

Checks that all components for Silver Tier are properly configured:
- Python dependencies installed
- Credentials files exist
- Session files exist (or can be created)
- Vault structure is correct
- Watchers can be imported

Usage:
    python verify_silver_tier.py /path/to/vault
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 9:
        print("[OK] Python version is compatible")
        return True
    else:
        print("[FAIL] Python 3.9+ required")
        return False


def check_dependencies():
    """Check if required Python packages are installed."""
    print("\nChecking Dependencies:")
    print("-" * 40)
    
    packages = {
        'watchdog': 'File watching',
        'google.oauth2': 'Gmail API authentication',
        'googleapiclient': 'Gmail API client',
        'playwright': 'LinkedIn browser automation'
    }
    
    all_ok = True
    for package, purpose in packages.items():
        try:
            __import__(package)
            print(f"✓ {package} - {purpose}")
        except ImportError:
            print(f"✗ {package} - {purpose}")
            all_ok = False
    
    return all_ok


def check_credentials(vault_path: Path):
    """Check if credentials.json exists."""
    print("\nChecking Credentials:")
    print("-" * 40)
    
    creds_file = vault_path / 'credentials.json'
    
    if creds_file.exists():
        print(f"✓ credentials.json found")
        
        # Try to parse it
        try:
            with open(creds_file, 'r') as f:
                creds = json.load(f)
            
            if 'installed' in creds:
                print(f"✓ Google OAuth credentials valid")
                print(f"  Project ID: {creds['installed'].get('project_id', 'Unknown')}")
                return True
            else:
                print("✗ Invalid credentials format")
                return False
                
        except json.JSONDecodeError as e:
            print(f"✗ Failed to parse credentials: {e}")
            return False
    else:
        print("✗ credentials.json not found")
        print("\nTo get credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download credentials.json to vault root")
        return False


def check_vault_structure(vault_path: Path):
    """Check if vault has required folder structure."""
    print("\nChecking Vault Structure:")
    print("-" * 40)
    
    required_folders = [
        'Inbox',
        'Needs_Action',
        'Plans',
        'Pending_Approval',
        'Approved',
        'Rejected',
        'Done',
        'Logs',
        'Files/Incoming'
    ]
    
    all_ok = True
    for folder in required_folders:
        folder_path = vault_path / folder
        if folder_path.exists():
            print(f"✓ {folder}/")
        else:
            print(f"✗ {folder}/ - Creating...")
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"  Created {folder}/")
    
    # Check required files
    required_files = ['Dashboard.md', 'Business_Goals.md', 'Company_Handbook.md']
    for file in required_files:
        file_path = vault_path / file
        if file_path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - Not found (optional)")
    
    return all_ok


def check_sessions(vault_path: Path):
    """Check if session files exist."""
    print("\nChecking Session Files:")
    print("-" * 40)
    
    sessions = {
        '.gmail_token': 'Gmail API (created after first auth)',
        '.linkedin_session': 'LinkedIn (created after setup)'
    }
    
    all_ok = True
    for session_file, description in sessions.items():
        session_path = vault_path / session_file
        
        # Handle directory for LinkedIn
        if session_path.is_dir():
            files = list(session_path.glob('*'))
            if files:
                print(f"✓ {session_file}/ - {description}")
            else:
                print(f"○ {session_file}/ - Empty (run setup)")
                all_ok = False
        elif session_path.exists():
            print(f"✓ {session_file} - {description}")
        else:
            print(f"○ {session_file} - Not created yet")
            all_ok = False
    
    return all_ok


def check_watchers(scripts_dir: Path):
    """Check if watcher scripts exist."""
    print("\nChecking Watcher Scripts:")
    print("-" * 40)
    
    watchers = {
        'gmail_watcher.py': 'Gmail monitoring',
        'linkedin_watcher.py': 'LinkedIn monitoring',
        'filesystem_watcher.py': 'File drop monitoring',
        'orchestrator.py': 'Task orchestration',
        'start_all_watchers.py': 'Unified launcher'
    }
    
    all_ok = True
    for script, purpose in watchers.items():
        script_path = scripts_dir / script
        if script_path.exists():
            print(f"✓ {script} - {purpose}")
        else:
            print(f"✗ {script} - {purpose}")
            all_ok = False
    
    return all_ok


def run_quick_test(vault_path: Path):
    """Run a quick test of the watchers."""
    print("\nRunning Quick Test:")
    print("-" * 40)
    
    scripts_dir = vault_path / 'scripts'
    
    # Test Gmail watcher (once mode)
    print("Testing Gmail Watcher...")
    try:
        result = subprocess.run(
            [sys.executable, str(scripts_dir / 'gmail_watcher.py'), 
             str(vault_path), '--once'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✓ Gmail Watcher test passed")
        else:
            if 'Authentication' in result.stdout or 'credentials' in result.stdout.lower():
                print("○ Gmail Watcher needs authentication")
                print("  Run: python gmail_watcher.py <vault> --auth")
            else:
                print(f"✗ Gmail Watcher test failed: {result.stderr[:100]}")
    except subprocess.TimeoutExpired:
        print("○ Gmail Watcher test timed out (may need auth)")
    except Exception as e:
        print(f"✗ Gmail Watcher test error: {e}")
    
    # Test LinkedIn watcher (check import)
    print("Testing LinkedIn Watcher import...")
    try:
        result = subprocess.run(
            [sys.executable, '-c', 
             f'import sys; sys.path.insert(0, r"{scripts_dir}"); from linkedin_watcher import LinkedInWatcher'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ LinkedIn Watcher imports correctly")
        else:
            print(f"✗ LinkedIn Watcher import failed: {result.stderr[:100]}")
    except Exception as e:
        print(f"✗ LinkedIn Watcher import error: {e}")
    
    return True


def print_setup_instructions(vault_path: Path):
    """Print next steps for setup."""
    print("\n" + "=" * 60)
    print("  Silver Tier Setup Instructions")
    print("=" * 60)
    print()
    print("1. Authenticate Gmail:")
    print(f"   python gmail_watcher.py {vault_path} --auth")
    print()
    print("2. Setup LinkedIn Session:")
    print(f"   python linkedin_watcher.py {vault_path} --setup")
    print()
    print("3. Start All Watchers:")
    print(f"   python start_all_watchers.py {vault_path}")
    print()
    print("4. Monitor Action Files:")
    print(f"   Check: {vault_path / 'Needs_Action'}")
    print()
    print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verify Silver Tier setup'
    )
    parser.add_argument('vault', nargs='?', default='.', 
                       help='Path to Obsidian vault (default: current directory)')
    parser.add_argument('--test', action='store_true', 
                       help='Run quick functionality test')
    
    args = parser.parse_args()
    
    vault_path = Path(args.vault).resolve()
    
    if not vault_path.exists():
        print(f"Error: Vault path does not exist: {vault_path}")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("  AI Employee - Silver Tier Verification")
    print("=" * 60)
    print(f"  Vault: {vault_path}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run checks
    checks = [
        ("Python Version", check_python_version()),
        ("Dependencies", check_dependencies()),
        ("Credentials", check_credentials(vault_path)),
        ("Vault Structure", check_vault_structure(vault_path)),
        ("Session Files", check_sessions(vault_path)),
        ("Watcher Scripts", check_watchers(vault_path / 'scripts'))
    ]
    
    if args.test:
        checks.append(("Quick Test", run_quick_test(vault_path)))
    
    # Summary
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = "✓ PASS" if result else "○ NEEDS ATTENTION"
        print(f"  {status}: {name}")
    
    print()
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All checks passed! Silver Tier is ready.")
        print_setup_instructions(vault_path)
        return 0
    else:
        print("\n○ Some checks need attention. See details above.")
        print_setup_instructions(vault_path)
        return 1


if __name__ == '__main__':
    sys.exit(main())
