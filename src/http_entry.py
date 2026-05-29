"""
HTTP entry point for Render.com / Smithery.
Binds to 0.0.0.0:<PORT> so Render can detect the open port.

Usage:
    python -m src.http_entry
"""
import os
import sys

# Re-use dev mode detection from server module
sys.argv.append("--http")
if os.getenv("DEV_MODE", "1") == "1":
    sys.argv.append("--dev")

# Patch environment to force uvicorn to listen on all interfaces
os.environ["UVICORN_HOST"] = "0.0.0.0"
os.environ["UVICORN_PORT"] = os.getenv("PORT", "8000")

from src.server import main

if __name__ == "__main__":
    main()
