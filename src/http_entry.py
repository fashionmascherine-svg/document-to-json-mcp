"""
HTTP entry point for Render.com / Smithery.
Serves MCP at /mcp and server-card.json at /.well-known/mcp/server-card.json
for Smithery discovery (skips scan).
"""
import os, sys, json, logging
if "--dev" not in sys.argv:
    sys.argv.insert(1, "--dev")
os.environ["DEV_MODE"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
logger = logging.getLogger("document-to-json-mcp.http")

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

# Server card for Smithery discovery
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

async def server_card(request):
    return JSONResponse(SERVER_CARD)

async def root(request):
    return JSONResponse({"status": "ok", "message": "Document-to-JSON MCP Server", "endpoint": "/mcp"})

# Create app with server card route BEFORE MCP mount
# Smithery reads this to skip full scan
from starlette.routing import Route
card_app = Starlette(routes=[
    Route("/.well-known/mcp/server-card.json", server_card),
    Route("/", root),
])

# Mount the MCP app
from starlette.routing import Mount
mcp_app = mcp.streamable_http_app()
card_app.router.routes.append(Mount("/mcp", app=mcp_app))

logger.info(f"Starting on {host}:{port}")
logger.info(f"MCP endpoint: /mcp")
logger.info(f"Server card: /.well-known/mcp/server-card.json")
logger.info("Smithery will skip scan via server-card.json")

uvicorn.run(card_app, host=host, port=port, log_level="info")
