# -*- coding: utf-8 -*-
"""Main entry point for Local Deep Research application.

This is the root-level main.py that can launch the FastAPI server.

Usage:
    python main.py

Or with environment variables:
    export API_PORT=8000
    python main.py
"""
import os
import sys
from pathlib import Path

# Get the directory containing this file (local_deep_research/)
current_dir = Path(__file__).resolve().parent

# Add parent directory to Python path so we can import local_deep_research as a package
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Also add current directory to path
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def main():
    """Main entry point."""
    print("=" * 80)
    print("Starting Local Deep Research API Server")
    print("=" * 80)
    print(f"Current directory: {current_dir}")
    print(f"Parent directory: {parent_dir}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")
    print("=" * 80)

    # Import here after path is set up
    try:
        from local_deep_research.api.main import main as api_main
        api_main()
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nTrying alternative import method...")

        # Try importing from api directly
        try:
            from api.main import main as api_main
            api_main()
        except ImportError as e2:
            print(f"❌ Alternative import also failed: {e2}")
            print("\nPlease ensure you're running from the correct directory:")
            print(f"  cd {current_dir}")
            print("  python main.py")
            sys.exit(1)


if __name__ == "__main__":
    main()
