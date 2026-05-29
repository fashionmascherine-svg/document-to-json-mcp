"""
HTTP entry point for Render.com / Smithery.
Binds to 0.0.0.0:<PORT> so Render can detect the open port.
Also serves /.well-known/mcp/server-card.json for Smithery discovery.

Usage:
    python -m src.http_entry
"""
import os
import sys
import logging
import json

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
from starlette.routing import Route
from starlette.responses import JSONResponse
from src.server import mcp

port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")

# Server card for MCP discovery (helps Smithery skip scanning)
SERVER_CARD = {
    "name": "document-to-json-mcp",
    "description": "Convert PDF documents to structured JSON. Extract invoices, bank statements, contracts, and more.",
    "version": "0.1.0",
    "tools": [
        {
            "name": "parse_invoice",
            "description": "Extract structured data from an invoice PDF",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_url": {"type": "string", "description": "Public URL of the invoice PDF"},
                    "language": {"type": "string", "description": "Language hint (e.g., 'ita', 'eng')", "default": "ita+eng"}
                },
                "required": ["file_url"]
            }
        },
        {
            "name": "parse_bank_statement",
            "description": "Extract transactions, balances, and fees from a bank statement PDF",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_url": {"type": "string", "description": "Public URL of the bank statement PDF"},
                    "language": {"type": "string", "description": "Language hint", "default": "ita+eng"}
                },
                "required": ["file_url"]
            }
        },
        {
            "name": "parse_contract",
            "description": "Extract parties, clauses, dates, and terms from a contract PDF",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_url": {"type": "string", "description": "Public URL of the contract PDF"},
                    "language": {"type": "string", "description": "Language hint", "default": "ita+eng"}
                },
                "required": ["file_url"]
            }
        },
        {
            "name": "parse_generic_document",
            "description": "Extract text and tables from any PDF document",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_url": {"type": "string", "description": "Public URL of the PDF"},
                    "language": {"type": "string", "description": "Language hint", "default": "ita+eng"}
                },
                "required": ["file_url"]
            }
        },
        {
            "name": "supported_document_types",
            "description": "List all supported document types (free tool)",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]
}

async def server_card(request):
    return JSONResponse(SERVER_CARD)

# Get the MCP Starlette app
streamable_app = mcp.streamable_http_app()

# Create combined app with the server card route
combined = Starlette(
    routes=[
        Route("/.well-known/mcp/server-card.json", endpoint=server_card),
    ]
)

# Mount the MCP app at /mcp and root
from starlette.routing import Mount

combined.router.routes.append(Mount("/", app=streamable_app))

logger.info(f"Starting Document-to-JSON MCP Server via uvicorn on {host}:{port}...")
logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
logger.info(f"Server card: http://{host}:{port}/.well-known/mcp/server-card.json")

uvicorn.run(combined, host=host, port=port, log_level="info")
