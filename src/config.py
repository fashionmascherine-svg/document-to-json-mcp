"""
Configuration module for Document-to-JSON MCP Server.
Loads settings from environment variables (.env file or system env).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM API (OpenAI-compatible) ───────────────────────────────────
# Provider-agnostic. Set these as environment variables (no provider-revealing
# defaults are hardcoded here): LLM_API_KEY, LLM_MODEL, LLM_BASE_URL.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

# ─── x402 Payment (USDC on Base) ───────────────────────────────────
X402_WALLET_ADDRESS = os.getenv("X402_WALLET_ADDRESS", "")
X402_NETWORK = os.getenv("X402_NETWORK", "eip155:8453")  # Base mainnet

# ─── Processing Limits ─────────────────────────────────────────────
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "50"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "eng+ita+spa")

# ─── Pricing per tool (USD) — launch prices, kept in sync with the ──
# ─── Apify Console Monetization (PAY_PER_EVENT) for display only. ───
PRICES: dict[str, float] = {
    "parse_invoice": 0.01,             # $0.01 per invoice (launch)
    "parse_bank_statement": 0.015,     # $0.015 per bank statement (launch)
    "parse_contract": 0.02,            # $0.02 per contract (launch)
    "parse_generic_document": 0.0,     # free during launch (the hook)
}

# ─── Free Tier Limits ──────────────────────────────────────────────
FREE_TIER_MAX_CALLS_PER_DAY = 3
FREE_TIER_MAX_FILE_SIZE_MB = 5
FREE_TOOLS = {"supported_document_types"}  # Always free tools
