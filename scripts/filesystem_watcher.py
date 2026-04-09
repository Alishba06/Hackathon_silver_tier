"""
File System Watcher - Monitors a drop folder for new files.

This is the simplest watcher for the Bronze tier. It watches a designated
"Inbox" folder and creates action files whenever new files are dropped in.

Usage:
    python filesystem_watcher.py /path/to/vault

The watcher will monitor the /Inbox folder and copy new files to
/Needs_Action with accompanying metadata files.
"""

import time
import logging
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

# Try to import watchdog, fall back to polling if not available
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning('watchdog not installed, using polling fallback')

from base_watcher import BaseWatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class DropFolderHandler(FileSystemEventHandler):
    """Handle file system events for the drop folder."""
    
    def __init__(self, vault_path: str, watcher_callback):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.watcher_callback = watcher_callback
        self.logger = logging.getLogger('DropFolderHandler')
    
    def on_created(self, event):
        """Called when a file or directory is created."""
        if event.is_directory:
            return
        
        source = Path(event.src_path)
        
        # Skip hidden files and temporary files
        if source.name.startswith('.') or source.suffix == '.tmp':
            return
        
        self.logger.info(f'New file detected: {source.name}')
        self.watcher_callback(source)


class FilesystemWatcher(BaseWatcher):
    """
    Watches the Inbox folder for new files.
    
    When a file is dropped into /Inbox, it:
    1. Copies the file to /Needs_Action
    2. Creates a metadata .md file with file info
    """
    
    def __init__(self, vault_path: str, check_interval: int = 30):
        super().__init__(vault_path, check_interval)
        self.inbox = self.vault_path / 'Inbox'
        self.files_folder = self.vault_path / 'Files'
        
        # Ensure folders exist
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.files_folder.mkdir(parents=True, exist_ok=True)
        
        # Track processed files by hash
        self.processed_hashes = set()
    
    def check_for_updates(self) -> list:
        """Check the Inbox folder for new files."""
        new_files = []
        
        try:
            for file_path in self.inbox.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    # Calculate file hash for deduplication
                    file_hash = self._calculate_hash(file_path)
                    
                    if file_hash not in self.processed_hashes:
                        new_files.append(file_path)
                        self.processed_hashes.add(file_hash)
        except Exception as e:
            self.logger.error(f'Error scanning inbox: {e}')
        
        return new_files
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file for deduplication."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f'Error calculating hash: {e}')
            return str(time.time())
    
    def create_action_file(self, file_path: Path) -> Path:
        """
        Create an action file for the dropped file.

        Moves the file to Needs_Action and creates metadata.
        """
        # Get file info BEFORE moving (file won't exist in Inbox after move)
        file_size = file_path.stat().st_size
        original_name = file_path.name
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'FILE_{original_name}'

        # Move file to Needs_Action (not copy - we want to move it)
        dest = self.needs_action / filename
        try:
            # Use shutil.move for proper file move across drives
            shutil.move(str(file_path), str(dest))
            self.logger.info(f'Moved file to: {dest}')
        except Exception as e:
            self.logger.error(f'Error moving file: {e}')
            # Fallback to copy if move fails
            try:
                with open(file_path, 'rb') as src:
                    content = src.read()
                with open(dest, 'wb') as dst:
                    dst.write(content)
                self.logger.info(f'Copied file to: {dest} (move failed)')
            except Exception as e2:
                self.logger.error(f'Fallback copy also failed: {e2}')
                dest = self.needs_action / f'{filename}.error'
                dest.write_text(f'Error moving file: {e}\nFallback error: {e2}')

        # Create metadata file
        meta_path = self.needs_action / f'{filename}.meta.md'

        content = f'''---
type: file_drop
original_name: {original_name}
size: {file_size}
received: {datetime.now().isoformat()}
status: pending
source: Inbox
---

# File Dropped for Processing

**Original Name:** {original_name}

**Size:** {self._format_size(file_size)}

**Location:** `{filename}`

## Suggested Actions

- [ ] Review file contents
- [ ] Process or take action
- [ ] Move to /Done when complete

## Notes

*Add your notes here*

---
*Created by Filesystem Watcher v0.1*
'''
        meta_path.write_text(content)
        self.logger.info(f'Created metadata file: {meta_path.name}')
        
        return meta_path
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f'{size_bytes:.2f} {unit}'
            size_bytes /= 1024.0
        return f'{size_bytes:.2f} TB'
    
    def run_with_watchdog(self):
        """Run using watchdog for real-time monitoring (if available)."""
        if not WATCHDOG_AVAILABLE:
            self.logger.warning('watchdog not available, falling back to polling')
            return self.run()
        
        self.logger.info(f'Starting {self.__class__.__name__} (watchdog mode)')
        self.logger.info(f'Watching folder: {self.inbox}')
        
        event_handler = DropFolderHandler(str(self.vault_path), self.create_action_file)
        observer = Observer()
        observer.schedule(event_handler, str(self.inbox), recursive=False)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


def main():
    """Main entry point."""
    import sys
    
    # Get vault path from command line or use current directory
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]
    else:
        vault_path = '.'
    
    vault_path = Path(vault_path).resolve()
    
    if not vault_path.exists():
        print(f'Error: Vault path does not exist: {vault_path}')
        sys.exit(1)
    
    print(f'AI Employee - Filesystem Watcher v0.1 (Bronze Tier)')
    print(f'Vault: {vault_path}')
    print(f'Watching: {vault_path / "Inbox"}')
    print(f'Output: {vault_path / "Needs_Action"}')
    print()
    
    command = sys.argv[2] if len(sys.argv) > 2 else 'watch'
    watcher = FilesystemWatcher(str(vault_path))
    
    if command == 'run':
        # Single run mode - process existing files and exit
        print('Single run mode - processing existing files...')
        items = watcher.check_for_updates()
        for item in items:
            filepath = watcher.create_action_file(item)
            print(f'Created: {filepath.name}')
        if not items:
            print('No new files to process.')
        else:
            print(f'Processed {len(items)} file(s).')
    else:
        # Watch mode - continuous monitoring
        print('Drop files into the /Inbox folder to create action items.')
        print('Press Ctrl+C to stop.')
        print()
        
        # Try watchdog mode first, fall back to polling
        if WATCHDOG_AVAILABLE:
            watcher.run_with_watchdog()
        else:
            watcher.run()


if __name__ == '__main__':
    main()
