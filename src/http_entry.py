"""
HTTP entry point for Render.com / Smithery.
Binds to 0.0.0.0:<PORT> so Render can detect the open port.
Uses uvicorn directly instead of FastMCP.run().

Usage:
    python -m src.http_entry
"""
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("document-to-json-mcp.http")

# Enable dev mode before importing server
if os.getenv("DEV_MODE", "1") == "1":
    sys.argv.append("--dev")

import uvicorn
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

logger.info(f"Starting Document-to-JSON MCP Server via uvicorn on {host}:{port}...")
logger.info(f"Connect to: http://{host}:{port}/mcp (streamable-http)")

# Directly serve the FastMCP Starlette app with proper binding
starlette_app = mcp.streamable_http_app()
uvicorn.run(starlette_app, host=host, port=port, log_level="info")
