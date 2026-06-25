#!/bin/bash
# Start script for Render.com HTTP hosting
# Binds to 0.0.0.0:$PORT for Render to detect
set -e

PORT="${PORT:-8000}"
echo "Starting Document-to-JSON MCP Server on 0.0.0.0:$PORT..."

# Use uvicorn directly to have full control over host:port binding
exec uvicorn src.server:mcp --host 0.0.0.0 --port "$PORT"
