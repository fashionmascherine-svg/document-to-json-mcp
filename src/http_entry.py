"""
HTTP entry point for Render.com / Smithery.
Binds to 0.0.0.0:<PORT> so Render can detect the open port.

Usage:
    python -m src.http_entry
"""
import os
import sys

# CRITICAL: Set env vars BEFORE importing server
# FastMCP reads these in its constructor for host/port binding
os.environ.setdefault("HOST", "0.0.0.0")
os.environ.setdefault("PORT", os.getenv("PORT", "8000"))

# Enable dev mode
if os.getenv("DEV_MODE", "1") == "1":
    sys.argv.append("--dev")

# Now import and run the server
from src.server import main
sys.argv.append("--http")
main()
