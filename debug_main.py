#!/usr/bin/env python
"""Debug script to capture main.py error"""

import sys
import traceback

try:
    print("Starting main.py import...")
    import main
    print("Successfully imported main")
except Exception as e:
    print(f"ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    print("\nFull Traceback:")
    traceback.print_exc()
    sys.exit(1)
