"""
HTTP entry point for Render.com / Smithery.
Simple approach: serve MCP directly at root.
"""
import os, sys, logging
if "--dev" not in sys.argv:
    sys.argv.insert(1, "--dev")
os.environ["DEV_MODE"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
logger = logging.getLogger("document-to-json-mcp.http")

import uvicorn
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

logger.info(f"Starting on {host}:{port}")

# Use the app directly at root - no sub-path mounting
app = mcp.streamable_http_app()

uvicorn.run(app, host=host, port=port, log_level="info")
