"""
Configuration module for Document-to-JSON MCP Server.
Loads settings from environment variables (.env file or system env).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── DeepSeek API ───────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ─── x402 Payment (USDC on Base) ───────────────────────────────────
X402_WALLET_ADDRESS = os.getenv("X402_WALLET_ADDRESS", "")
X402_NETWORK = os.getenv("X402_NETWORK", "eip155:8453")  # Base mainnet

# ─── Processing Limits ─────────────────────────────────────────────
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "50"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ita+eng")

# ─── Pricing per tool (USD) ────────────────────────────────────────
PRICES: dict[str, float] = {
    "parse_invoice": 0.02,            # $0.02 per invoice
    "parse_bank_statement": 0.03,     # $0.03 per bank statement
    "parse_contract": 0.05,           # $0.05 per contract
    "parse_generic_document": 0.01,   # $0.01 per generic doc
}

# ─── Free Tier Limits ──────────────────────────────────────────────
FREE_TIER_MAX_CALLS_PER_DAY = 3
FREE_TIER_MAX_FILE_SIZE_MB = 5
FREE_TOOLS = {"supported_document_types"}  # Always free tools
