#!/usr/bin/env python3
"""
Command-line reply helper for WoodworkersArchive Community Engagement Engine.

This script provides a convenient way to generate compliant replies
with UTM tracking for community posts.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.reply_kit import create_cli_tool

if __name__ == "__main__":
    cli_main = create_cli_tool()
    sys.exit(cli_main())

