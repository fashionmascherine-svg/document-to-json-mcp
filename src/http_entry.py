"""
HTTP entry point for Render.com / Smithery.
Binds to 0.0.0.0:<PORT> so Render can detect the open port.
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
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

# Get the MCP StreamableHTTP ASGI app
streamable_app = mcp.streamable_http_app()

class ServerCardMiddleware(BaseHTTPMiddleware):
    """Middleware to serve server-card.json before MCP handles the request."""
    SERVER_CARD = {
        "name": "document-to-json-mcp",
        "description": "Convert PDF documents to structured JSON. Extract invoices, bank statements, contracts, and more.",
        "version": "0.1.0",
        "tools": [
            {"name": "parse_invoice", "description": "Extract structured data from an invoice PDF", "inputSchema": {"type": "object", "properties": {"file_url": {"type": "string"}, "language": {"type": "string", "default": "ita+eng"}}, "required": ["file_url"]}},
            {"name": "parse_bank_statement", "description": "Extract transactions from a bank statement PDF", "inputSchema": {"type": "object", "properties": {"file_url": {"type": "string"}, "language": {"type": "string", "default": "ita+eng"}}, "required": ["file_url"]}},
            {"name": "parse_contract", "description": "Extract parties and clauses from a contract PDF", "inputSchema": {"type": "object", "properties": {"file_url": {"type": "string"}, "language": {"type": "string", "default": "ita+eng"}}, "required": ["file_url"]}},
            {"name": "parse_generic_document", "description": "Extract text from any PDF", "inputSchema": {"type": "object", "properties": {"file_url": {"type": "string"}, "language": {"type": "string", "default": "ita+eng"}}, "required": ["file_url"]}},
            {"name": "supported_document_types", "description": "List supported document types", "inputSchema": {"type": "object", "properties": {}}}
        ]
    }
    
    async def dispatch(self, request, call_next):
        if request.url.path == "/.well-known/mcp/server-card.json":
            return JSONResponse(self.SERVER_CARD)
        return await call_next(request)

# Wrap the MCP app with our middleware
app = ServerCardMiddleware(streamable_app)

logger.info(f"Starting Document-to-JSON MCP Server via uvicorn on {host}:{port}...")
logger.info(f"MCP endpoint: http://{host}:{port}/mcp")

uvicorn.run(streamable_app, host=host, port=port, log_level="info")
