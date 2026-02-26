"""
Veltrix Language — Entry Point
===============================
Run this file to execute .vlx programs or start the REPL.

Usage:
    python main.py run <file.vlx>
    python main.py repl
    python main.py help
"""

import sys
import os

# Add the project root to the path so 'veltrix' package can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from veltrix.cli import main

if __name__ == "__main__":
    main()
