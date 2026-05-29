"""
HTTP entry point for Render.com / Smithery.
Binds to 0.0.0.0:<PORT> so Render can detect the open port.
Disables Host header validation for proxy compatibility.

Usage:
    python -m src.http_entry
"""
import os
import sys

# CRITICAL: Set --dev BEFORE importing server module
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
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

logger.info(f"Starting Document-to-JSON MCP Server via uvicorn on {host}:{port}...")
logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
logger.info("Dev mode: PayMCP/x402 disabled")

# Get the MCP Starlette app
streamable_app = mcp.streamable_http_app()

# Wrap with middleware to allow all hosts (needed for Render/Smithery proxy)
app = Starlette(
    middleware=[
        Middleware(TrustedHostMiddleware, allowed_hosts=["*"]),
    ]
)

# Mount the MCP app at /mcp
from starlette.routing import Mount
app.router.routes.append(Mount("/mcp", app=streamable_app))
# Also mount at root for direct access
app.router.routes.append(Mount("/", app=streamable_app))

uvicorn.run(app, host=host, port=port, log_level="info")
