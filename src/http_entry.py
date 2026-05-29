"""
HTTP entry point for Render.com / Smithery.
Must set --dev BEFORE importing server module.
Binds to 0.0.0.0:<PORT> so Render can detect the open port.

Usage:
    python -m src.http_entry
"""
import os
import sys

# CRITICAL: Set --dev BEFORE importing server module
# because DEV_MODE is checked at import time
if "--dev" not in sys.argv:
    sys.argv.insert(1, "--dev")
os.environ["DEV_MODE"] = "1"

import logging
logger = logging.getLogger("document-to-json-mcp.http")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)

import uvicorn
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

logger.info(f"Starting Document-to-JSON MCP Server via uvicorn on {host}:{port}...")
logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
logger.info("Dev mode: PayMCP/x402 disabled")

starlette_app = mcp.streamable_http_app()
uvicorn.run(starlette_app, host=host, port=port, log_level="info")
