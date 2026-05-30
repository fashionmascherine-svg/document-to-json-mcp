"""
HTTP entry point for Render.com / Smithery.
Serves MCP at /mcp and server-card at /.well-known/mcp/server-card.json
"""
import os, sys, json, logging
if "--dev" not in sys.argv:
    sys.argv.insert(1, "--dev")
os.environ["DEV_MODE"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
logger = logging.getLogger("document-to-json-mcp.http")

import uvicorn
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

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

class ServerCardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/.well-known/mcp/server-card.json":
            return JSONResponse(SERVER_CARD)
        return await call_next(request)

# Get the raw MCP app (it already handles /mcp internally)
app = mcp.streamable_http_app()
# Wrap with middleware to serve server-card before MCP handles it
app.add_middleware(ServerCardMiddleware)

logger.info(f"Starting on {host}:{port}")
logger.info(f"MCP endpoint: /mcp")
logger.info(f"Server card: /.well-known/mcp/server-card.json")

uvicorn.run(app, host=host, port=port, log_level="info")
