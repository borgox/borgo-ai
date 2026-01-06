#!/usr/bin/env python3
"""
Borgo-AI CLI Runner
"""
import sys
import os

# Try to import from installed package first
try:
    import borgo_ai.main
    borgo_ai.main.main()
except ImportError:
    # Fall back to local development mode
    # Add src directory to path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(script_dir, 'src')
    sys.path.insert(0, src_dir)

    # Import the package
    import borgo_ai.main
    borgo_ai.main.main()