"""
Base Watcher - Abstract base class for all AI Employee watchers.

Watchers are lightweight Python scripts that run continuously in the background,
monitoring various inputs (Gmail, WhatsApp, filesystems) and creating actionable
files for Claude Code to process.
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class BaseWatcher(ABC):
    """
    Abstract base class for all watchers.
    
    All watchers follow the same pattern:
    1. Check for new items (emails, messages, files, etc.)
    2. Create .md action files in the Needs_Action folder
    3. Track processed items to avoid duplicates
    """
    
    def __init__(self, vault_path: str, check_interval: int = 60):
        """
        Initialize the watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            check_interval: How often to check for new items (in seconds)
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Ensure Needs_Action folder exists
        self.needs_action.mkdir(parents=True, exist_ok=True)
        
        # Track processed items to avoid duplicates
        self.processed_ids = set()
    
    @abstractmethod
    def check_for_updates(self) -> list:
        """
        Check for new items to process.
        
        Returns:
            List of new items that need action
        """
        pass
    
    @abstractmethod
    def create_action_file(self, item) -> Path:
        """
        Create a .md action file in the Needs_Action folder.
        
        Args:
            item: The item to create an action file for
            
        Returns:
            Path to the created file
        """
        pass
    
    def run(self):
        """
        Main run loop. Continuously checks for updates and creates action files.
        """
        self.logger.info(f'Starting {self.__class__.__name__}')
        self.logger.info(f'Vault path: {self.vault_path}')
        self.logger.info(f'Check interval: {self.check_interval}s')
        
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    filepath = self.create_action_file(item)
                    self.logger.info(f'Created action file: {filepath.name}')
            except Exception as e:
                self.logger.error(f'Error checking for updates: {e}')
            
            time.sleep(self.check_interval)
    
    def generate_filename(self, prefix: str, unique_id: str) -> str:
        """
        Generate a unique filename for an action file.
        
        Args:
            prefix: File prefix (e.g., 'EMAIL', 'WHATSAPP', 'FILE')
            unique_id: Unique identifier for the item
            
        Returns:
            Filename with .md extension
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'{prefix}_{unique_id}_{timestamp}.md'
    
    def create_yaml_frontmatter(self, data: dict) -> str:
        """
        Create YAML frontmatter for an action file.
        
        Args:
            data: Dictionary of key-value pairs
            
        Returns:
            Formatted YAML frontmatter string
        """
        lines = ['---']
        for key, value in data.items():
            lines.append(f'{key}: {value}')
        lines.append('---')
        return '\n'.join(lines)
