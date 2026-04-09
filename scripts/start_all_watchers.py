"""
Start All Watchers - Silver Tier

Launches all configured watchers for the AI Employee:
- Gmail Watcher (monitors emails)
- LinkedIn Watcher (monitors notifications)
- File Watcher (monitors drop folder)
- Orchestrator (coordinates processing)

Usage:
    python start_all_watchers.py /path/to/vault

Or run individual watchers:
    python gmail_watcher.py /path/to/vault
    python linkedin_watcher.py /path/to/vault
    python filesystem_watcher.py /path/to/vault
"""

import subprocess
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('StartWatchers')


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    try:
        import watchdog
    except ImportError:
        missing.append('watchdog')
    
    try:
        from google.oauth2 import credentials
    except ImportError:
        missing.append('google-auth, google-auth-oauthlib, google-api-python-client')
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        missing.append('playwright')
    
    if missing:
        print("Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print()
        print("Install with: pip install -r requirements.txt")
        print()
        return False
    
    return True


def start_watcher(name: str, command: list, background: bool = True):
    """Start a watcher process."""
    logger.info(f"Starting {name}...")
    
    try:
        if background:
            # Start in background
            if sys.platform == 'win32':
                # Windows: use CREATE_NEW_CONSOLE
                import subprocess
                CREATE_NEW_CONSOLE = 0x00000010
                proc = subprocess.Popen(
                    command,
                    creationflags=CREATE_NEW_CONSOLE,
                    cwd=str(Path(command[0]).parent)
                )
            else:
                # Unix: use nohup
                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            logger.info(f"✓ {name} started (PID: {proc.pid})")
            return proc
        else:
            # Run in foreground
            subprocess.run(command)
            return None
            
    except Exception as e:
        logger.error(f"Failed to start {name}: {e}")
        return None


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Start all AI Employee watchers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python start_all_watchers.py /path/to/vault      # Start all watchers
  python start_all_watchers.py /path/to/vault --gmail    # Start only Gmail
  python start_all_watchers.py /path/to/vault --linkedin # Start only LinkedIn
  python start_all_watchers.py /path/to/vault --once     # Run once (not continuous)
        '''
    )
    parser.add_argument('vault', help='Path to Obsidian vault')
    parser.add_argument('--gmail', action='store_true', help='Start only Gmail Watcher')
    parser.add_argument('--linkedin', action='store_true', help='Start only LinkedIn Watcher')
    parser.add_argument('--file', action='store_true', help='Start only File Watcher')
    parser.add_argument('--orchestrator', action='store_true', help='Start orchestrator')
    parser.add_argument('--once', action='store_true', help='Run once (not continuous)')
    parser.add_argument('--visible', action='store_true', help='Run browsers in visible mode')
    
    args = parser.parse_args()
    
    vault_path = Path(args.vault).resolve()
    
    if not vault_path.exists():
        print(f"Error: Vault path does not exist: {vault_path}")
        sys.exit(1)
    
    scripts_dir = vault_path / 'scripts'
    
    print()
    print("=" * 60)
    print("  AI Employee - Silver Tier Watcher Launcher")
    print("=" * 60)
    print()
    print(f"Vault: {vault_path}")
    print()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Determine which watchers to start
    start_gmail = args.gmail or (not any([args.gmail, args.linkedin, args.file, args.orchestrator]))
    start_linkedin = args.linkedin or (not any([args.gmail, args.linkedin, args.file, args.orchestrator]))
    start_file = args.file or (not any([args.gmail, args.linkedin, args.file, args.orchestrator]))
    start_orchestrator = args.orchestrator or (not any([args.gmail, args.linkedin, args.file, args.orchestrator]))
    
    processes = []
    
    # Start Gmail Watcher
    if start_gmail:
        cmd = [
            sys.executable, str(scripts_dir / 'gmail_watcher.py'),
            str(vault_path),
            '-i', '120'
        ]
        if args.once:
            cmd.append('--once')
        proc = start_watcher("Gmail Watcher", cmd)
        if proc:
            processes.append(proc)
    
    # Start LinkedIn Watcher
    if start_linkedin:
        cmd = [
            sys.executable, str(scripts_dir / 'linkedin_watcher.py'),
            str(vault_path),
            '-i', '300'
        ]
        if args.visible:
            cmd.append('--visible')
        if args.once:
            cmd.append('--once')
        proc = start_watcher("LinkedIn Watcher", cmd)
        if proc:
            processes.append(proc)
    
    # Start File Watcher
    if start_file:
        cmd = [
            sys.executable, str(scripts_dir / 'filesystem_watcher.py'),
            str(vault_path)
        ]
        proc = start_watcher("File Watcher", cmd)
        if proc:
            processes.append(proc)
    
    # Start Orchestrator
    if start_orchestrator:
        cmd = [
            sys.executable, str(scripts_dir / 'orchestrator.py'),
            str(vault_path),
            'watch'
        ]
        proc = start_watcher("Orchestrator", cmd)
        if proc:
            processes.append(proc)
    
    print()
    print("All watchers started!")
    print()
    print("Summary:")
    if start_gmail:
        print("  ✓ Gmail Watcher - Checking every 120 seconds")
    if start_linkedin:
        print("  ✓ LinkedIn Watcher - Checking every 300 seconds")
    if start_file:
        print("  ✓ File Watcher - Monitoring Files/Incoming folder")
    if start_orchestrator:
        print("  ✓ Orchestrator - Processing items with Qwen Code")
    
    print()
    print("To stop: Close the terminal windows or press Ctrl+C")
    print()
    print("Watchers are creating action files in:")
    print(f"  {vault_path / 'Needs_Action'}")
    print()
    
    # If running in --once mode, wait for processes to complete
    if args.once:
        print("Running in --once mode. Waiting for completion...")
        for proc in processes:
            if proc:
                proc.wait()
        print("Done!")
        return
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping watchers...")
        for proc in processes:
            if proc:
                proc.terminate()
        print("All watchers stopped.")


if __name__ == '__main__':
    main()
