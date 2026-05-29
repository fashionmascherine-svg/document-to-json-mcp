"""
Document-to-JSON MCP Server
============================
Converts PDF documents to structured JSON using DeepSeek-v4-flash.
Pay-per-call via x402 protocol (USDC on Base).

Tools:
  - parse_invoice:           Extract structured data from invoice PDFs
  - parse_bank_statement:    Extract transactions from bank statement PDFs
  - parse_contract:          Extract clauses and metadata from contract PDFs
  - parse_generic_document:  Extract text and tables from any PDF
  - supported_document_types: List available document types (free)
"""
import asyncio
import logging
import sys
from typing import Optional

from src.config import (
    DEEPSEEK_API_KEY,
    X402_WALLET_ADDRESS,
    X402_NETWORK,
    PRICES,
    FREE_TIER_MAX_CALLS_PER_DAY,
    FREE_TIER_MAX_FILE_SIZE_MB,
    FREE_TOOLS,
)
from src.extractors.pdf import PDFExtractor, PDFExtractionError
from src.llm.deepseek import DeepSeekClient, DeepSeekError
from src.llm.prompts import (
    INVOICE_SYSTEM_PROMPT,
    BANK_STATEMENT_SYSTEM_PROMPT,
    CONTRACT_SYSTEM_PROMPT,
    GENERIC_SYSTEM_PROMPT,
)
from src.validation import validate_invoice, validate_bank_statement, validate_contract

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("document-to-json-mcp")

# ── MCP + PayMCP ────────────────────────────────────────────────────
from mcp.server.fastmcp import FastMCP, Context
from paymcp import PayMCP, Mode
from paymcp.providers import X402Provider, BasePaymentProvider

# ── Dev mode flag (bypass payment for testing) ────────────────────
import sys as _sys
DEV_MODE = "--dev" in _sys.argv

# ── Conditional price decorator ───────────────────────────────────
if DEV_MODE:
    # In dev mode, @price_if is a no-op (doesn't require payment)
    def price_if(price_amount: float = 0, currency: str = "USD"):
        """No-op price decorator for dev mode."""
        return lambda f: f
else:
    from paymcp import price as _price
    def price_if(price_amount: float = 0, currency: str = "USD"):
        """Real price decorator for production."""
        return _price(price=price_amount, currency=currency)

# ── Global instances ────────────────────────────────────────────────
mcp = FastMCP("document-to-json-mcp")
pdf_extractor = PDFExtractor()

# Configure PayMCP (only in production mode)
if not DEV_MODE and X402_WALLET_ADDRESS:
    PayMCP(
        mcp,
        providers=[
            X402Provider(
                pay_to=[{
                    "address": X402_WALLET_ADDRESS,
                    "network": X402_NETWORK,
                }]
            ),
        ],
        mode=Mode.AUTO,
    )
    logger.info(f"PayMCP configured with x402 wallet: {X402_WALLET_ADDRESS[:10]}... on {X402_NETWORK}")
else:
    logger.warning("X402_WALLET_ADDRESS not set. Payments disabled.")

# DeepSeek client — initialized lazily
_deepseek_client: Optional[DeepSeekClient] = None


def get_deepseek() -> DeepSeekClient:
    """Get or create the DeepSeek client singleton."""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient(
            api_key=DEEPSEEK_API_KEY,
        )
    return _deepseek_client


# ══════════════════════════════════════════════════════════════════════
# INVOICE SCHEMA (for DeepSeek function calling)
# ══════════════════════════════════════════════════════════════════════

INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["invoice"]},
        "confidence": {"type": "number"},
        "metadata": {
            "type": "object",
            "properties": {
                "invoice_number": {"type": "string"},
                "invoice_date": {"type": "string"},
                "due_date": {"type": "string"},
                "currency": {"type": "string"},
                "language": {"type": "string"},
            },
        },
        "seller": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "address": {"type": "string"},
                "vat_id": {"type": "string"},
                "fiscal_code": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
        },
        "buyer": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "address": {"type": "string"},
                "vat_id": {"type": "string"},
                "fiscal_code": {"type": "string"},
            },
        },
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "unit_of_measure": {"type": "string"},
                    "net_amount": {"type": "number"},
                    "vat_rate": {"type": "number"},
                    "vat_amount": {"type": "number"},
                    "total": {"type": "number"},
                },
            },
        },
        "totals": {
            "type": "object",
            "properties": {
                "net_total": {"type": "number"},
                "vat_total": {"type": "number"},
                "gross_total": {"type": "number"},
                "withholding_tax": {"type": "number"},
                "other_charges": {"type": "number"},
                "grand_total": {"type": "number"},
            },
        },
        "payment_info": {
            "type": "object",
            "properties": {
                "iban": {"type": "string"},
                "bank_name": {"type": "string"},
                "payment_terms": {"type": "string"},
            },
        },
    },
}

BANK_STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["bank_statement"]},
        "confidence": {"type": "number"},
        "metadata": {
            "type": "object",
            "properties": {
                "bank_name": {"type": "string"},
                "account_number": {"type": "string"},
                "statement_period": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                },
                "currency": {"type": "string"},
                "page_count": {"type": "integer"},
            },
        },
        "account_holder": {"type": "string"},
        "balances": {
            "type": "object",
            "properties": {
                "opening_balance": {"type": "number"},
                "closing_balance": {"type": "number"},
                "total_credits": {"type": "number"},
                "total_debits": {"type": "number"},
            },
        },
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                    "amount": {"type": "number"},
                    "type": {"type": "string", "enum": ["credit", "debit"]},
                    "category": {"type": "string"},
                    "balance_after": {"type": "number"},
                },
            },
        },
        "fees": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "amount": {"type": "number"},
                },
            },
        },
    },
}

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["contract"]},
        "confidence": {"type": "number"},
        "metadata": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "contract_date": {"type": "string"},
                "language": {"type": "string"},
                "page_count": {"type": "integer"},
            },
        },
        "parties": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "vat_id": {"type": "string"},
                },
            },
        },
        "dates": {
            "type": "object",
            "properties": {
                "effective_date": {"type": "string"},
                "expiry_date": {"type": "string"},
                "renewal_terms": {"type": "string"},
            },
        },
        "financial_terms": {
            "type": "object",
            "properties": {
                "fee": {"type": "number"},
                "currency": {"type": "string"},
                "payment_terms": {"type": "string"},
                "late_payment_penalty": {"type": "string"},
            },
        },
        "key_clauses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "clause_number": {"type": ["integer", "string"]},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                },
            },
        },
        "jurisdiction": {
            "type": "object",
            "properties": {
                "governing_law": {"type": "string"},
                "dispute_resolution": {"type": "string"},
            },
        },
    },
}

GENERIC_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["report", "letter", "memo", "article", "manual", "other"]},
        "confidence": {"type": "number"},
        "title": {"type": "string"},
        "document_date": {"type": "string"},
        "page_count": {"type": "integer"},
        "text_content": {"type": "string"},
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


# ══════════════════════════════════════════════════════════════════════
# TOOL: parse_invoice
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
@price_if(price_amount=PRICES["parse_invoice"], currency="USD")
async def parse_invoice(
    file_url: str,
    language: str = "ita+eng",
    extract_line_items: bool = True,
    validate_totals: bool = False,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Extract structured data from an invoice PDF.
    
    Returns JSON with seller, buyer, line items, totals, and payment info.
    Supports European (Fattura Elettronica) and international invoice formats.
    
    Args:
        file_url: Public URL of the PDF file (max 20MB).
        language: Document language(s) for OCR. Default: ita+eng.
        extract_line_items: Whether to extract individual line items. Default: true.
        validate_totals: Validate that line item sums match declared totals. Default: false.
    
    Cost: $0.02 per document, paid via x402 USDC on Base.
    """
    return await _process_document(
        file_url=file_url,
        system_prompt=INVOICE_SYSTEM_PROMPT,
        output_schema=INVOICE_SCHEMA,
        validation_fn=validate_invoice if validate_totals else None,
        document_type_label="invoice",
        ctx=ctx,
    )


# ══════════════════════════════════════════════════════════════════════
# TOOL: parse_bank_statement
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
@price_if(price_amount=PRICES["parse_bank_statement"], currency="USD")
async def parse_bank_statement(
    file_url: str,
    language: str = "ita+eng",
    categorize_transactions: bool = False,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Extract structured data from a bank statement PDF.
    
    Returns JSON with all transactions, balances, account holder info, and fees.
    
    Args:
        file_url: Public URL of the PDF file (max 20MB).
        language: Document language(s) for OCR. Default: ita+eng.
        categorize_transactions: Auto-categorize transactions. Default: false.
    
    Cost: $0.03 per document, paid via x402 USDC on Base.
    """
    prompt = BANK_STATEMENT_SYSTEM_PROMPT
    if categorize_transactions:
        prompt += "\n- Categorize transactions into: salary, utilities, food, transport, shopping, transfer, other"

    return await _process_document(
        file_url=file_url,
        system_prompt=prompt,
        output_schema=BANK_STATEMENT_SCHEMA,
        validation_fn=validate_bank_statement,
        document_type_label="bank_statement",
        ctx=ctx,
    )


# ══════════════════════════════════════════════════════════════════════
# TOOL: parse_contract
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
@price_if(price_amount=PRICES["parse_contract"], currency="USD")
async def parse_contract(
    file_url: str,
    language: str = "ita+eng",
    extract_clauses: bool = True,
    extract_financial_terms: bool = True,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Extract structured data from a contract PDF.
    
    Returns JSON with parties, key dates, financial terms, and essential clauses.
    
    Args:
        file_url: Public URL of the PDF file (max 20MB).
        language: Document language(s) for OCR. Default: ita+eng.
        extract_clauses: Extract key clauses (termination, confidentiality, etc.). Default: true.
        extract_financial_terms: Extract fees, payment terms, penalties. Default: true.
    
    Cost: $0.05 per document, paid via x402 USDC on Base.
    """
    return await _process_document(
        file_url=file_url,
        system_prompt=CONTRACT_SYSTEM_PROMPT,
        output_schema=CONTRACT_SCHEMA,
        validation_fn=validate_contract,
        document_type_label="contract",
        ctx=ctx,
    )


# ══════════════════════════════════════════════════════════════════════
# TOOL: parse_generic_document
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
@price_if(price_amount=PRICES["parse_generic_document"], currency="USD")
async def parse_generic_document(
    file_url: str,
    language: str = "ita+eng",
    extract_tables: bool = True,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Extract text and tables from any PDF document.
    
    Less structured than specialized parsers, but more flexible.
    Returns full text content and detected tables.
    
    Args:
        file_url: Public URL of the PDF file (max 20MB).
        language: Document language(s) for OCR. Default: ita+eng.
        extract_tables: Detect and extract tables. Default: true.
    
    Cost: $0.01 per document, paid via x402 USDC on Base.
    """
    return await _process_document(
        file_url=file_url,
        system_prompt=GENERIC_SYSTEM_PROMPT,
        output_schema=GENERIC_SCHEMA,
        document_type_label="generic",
        ctx=ctx,
    )


# ══════════════════════════════════════════════════════════════════════
# TOOL: supported_document_types (FREE)
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def supported_document_types() -> dict:
    """
    List all supported document types with their descriptions and prices.
    This tool is always free to call.
    """
    return {
        "document_types": [
            {
                "type": "invoice",
                "description": "Fatture, ricevute, note di credito/debito",
                "price_usd": PRICES["parse_invoice"],
                "confidence": "high",
            },
            {
                "type": "bank_statement",
                "description": "Estratti conto bancari",
                "price_usd": PRICES["parse_bank_statement"],
                "confidence": "high",
            },
            {
                "type": "contract",
                "description": "Contratti, accordi, NDA",
                "price_usd": PRICES["parse_contract"],
                "confidence": "medium",
            },
            {
                "type": "generic",
                "description": "Qualsiasi documento con testo e tabelle",
                "price_usd": PRICES["parse_generic_document"],
                "confidence": "medium",
            },
        ],
        "limits": {
            "max_file_size_mb": 20,
            "max_pages": 50,
            "free_tier_calls_per_day": 3,
        },
        "supported_languages": ["ita", "eng", "fra", "deu", "spa", "por"],
        "payment_method": "x402 USDC on Base mainnet",
        "payment_details": "Pay per call. No subscription required. USDC on Base network.",
    }


# ══════════════════════════════════════════════════════════════════════
# INTERNAL: shared document processing pipeline
# ══════════════════════════════════════════════════════════════════════

async def _process_document(
    file_url: str,
    system_prompt: str,
    output_schema: dict,
    document_type_label: str,
    ctx: Optional[Context] = None,
    validation_fn=None,
) -> dict:
    """
    Shared processing pipeline for all document types.
    
    1. Download PDF
    2. Extract text (native or OCR)
    3. Call DeepSeek for structured extraction
    4. Validate results
    5. Return JSON
    """
    try:
        # ── Step 1: Download PDF ────────────────────────────────
        await _report(ctx, 5, 100, f"Downloading PDF: {file_url[:50]}...")
        try:
            pdf_bytes = await pdf_extractor.download_pdf(file_url)
        except PDFExtractionError as e:
            return _error("download_failed", str(e))

        # ── Step 2: Extract text ────────────────────────────────
        await _report(ctx, 20, 100, "Extracting text from PDF...")
        try:
            text, used_ocr = pdf_extractor.extract_text(pdf_bytes)
        except PDFExtractionError as e:
            return _error("extraction_failed", str(e))

        if not text.strip():
            return _error("empty_document", "No text could be extracted from this PDF. The file may be empty or corrupted.")

        # ── Step 3: Call DeepSeek ───────────────────────────────
        await _report(ctx, 40, 100, f"Analyzing {document_type_label} with DeepSeek...")
        prompt = system_prompt
        if used_ocr:
            prompt += "\n\nNOTE: This document was processed with OCR. Be extra careful with number recognition and formatting."

        deepseek_client = get_deepseek()

        try:
            result = await deepseek_client.extract_structured(
                text=text,
                system_prompt=prompt,
                output_schema=output_schema,
            )
        except DeepSeekError as e:
            logger.error(f"DeepSeek extraction failed for {file_url[:50]}: {e}")
            return _error("llm_error", f"AI extraction failed: {str(e)}")

        # ── Step 4: Validation ──────────────────────────────────
        await _report(ctx, 80, 100, "Validating extracted data...")
        if validation_fn:
            try:
                warnings = validation_fn(result)
                if warnings:
                    result["validation_warnings"] = warnings
            except Exception as e:
                logger.warning(f"Validation error: {e}")

        # ── Step 5: Return result ───────────────────────────────
        result["used_ocr"] = used_ocr

        await _report(ctx, 100, 100, "Done.")
        return {"success": True, "data": result}

    except Exception as e:
        logger.exception(f"Unexpected error processing {file_url[:50]}")
        return _error("internal_error", f"An unexpected error occurred: {str(e)}")


def _error(code: str, message: str) -> dict:
    """Return a standardized error response."""
    logger.warning(f"Error [{code}]: {message}")
    return {"success": False, "error": code, "message": message}


async def _report(ctx: Optional[Context], current: int, total: int, message: str = None):
    """Report progress if context is available."""
    if ctx:
        try:
            if message:
                await ctx.report_progress(current, total)
                logger.debug(f"Progress: {current}/{total} - {message}")
            else:
                await ctx.report_progress(current, total)
        except Exception:
            pass  # Context reporting is non-critical


# ══════════════════════════════════════════════════════════════════════
# MAIN — supporta sia STDIO (default) che HTTP/SSE
# ══════════════════════════════════════════════════════════════════════

def main():
    """Entry point for the MCP server.
    
    Modalità STDIO (default): si connette via pipe standard.
    Modalità HTTP: python -m src.server --http (su http://localhost:$PORT/mcp)
    Modalità DEV (senza pagamento): python -m src.server --http --dev
    """
    import os
    import sys
    
    use_http = "--http" in sys.argv
    dev_mode = "--dev" in sys.argv
    port = int(os.getenv("PORT", "8000"))
    
    logger.info("Starting Document-to-JSON MCP Server...")
    logger.info(f"Prices: invoice=${PRICES['parse_invoice']}, "
                f"bank=${PRICES['parse_bank_statement']}, "
                f"contract=${PRICES['parse_contract']}, "
                f"generic=${PRICES['parse_generic_document']}")
    if dev_mode:
        logger.info("🧪 DEV MODE: All tools are free. No payment required.")
    elif X402_WALLET_ADDRESS:
        logger.info(f"x402 payments enabled → {X402_WALLET_ADDRESS[:10]}... on {X402_NETWORK}")
    else:
        logger.info("x402 payments DISABLED (no wallet configured)")
    
    if use_http:
        logger.info(f"Starting in HTTP mode on port {port}...")
        logger.info(f"Connect to: http://localhost:{port}/mcp (streamable-http)")
        if dev_mode:
            logger.info("🧪 DEV MODE active")
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting in STDIO mode (default)...")
        logger.info("For HTTP mode: python -m src.server --http --dev")
        mcp.run()


if __name__ == "__main__":
    main()
