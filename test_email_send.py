#!/usr/bin/env python3
"""Test email sender script"""

import subprocess
import sys

result = subprocess.run([
    sys.executable, 
    "scripts/gmail_mcp_sender.py",
    "recipient@example.com",
    "Test Subject",
    "Test body text"
], capture_output=False, text=True)

print(f"\nExit code: {result.returncode}")
