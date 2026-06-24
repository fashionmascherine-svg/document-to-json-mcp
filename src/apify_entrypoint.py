"""
Apify Actor entrypoint for Document-to-JSON Converter.
Processes a PDF from a URL and returns structured JSON.
Uses DeepSeek-v4-flash for AI-powered extraction.

Pricing (Pay-Per-Event, launch prices — set in Apify Console Monetization):
  - invoice-parsed:        $0.01
  - bank-statement-parsed: $0.015
  - contract-parsed:       $0.02
  - generic-parsed:        free during launch (~$0)
"""
import os
import sys
import json
import asyncio
import logging
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.pdf import PDFExtractor
from llm.deepseek import DeepSeekClient
from llm.prompts import (
    INVOICE_SYSTEM_PROMPT,
    BANK_STATEMENT_SYSTEM_PROMPT,
    CONTRACT_SYSTEM_PROMPT,
    GENERIC_SYSTEM_PROMPT,
)
from validation import validate_invoice, validate_bank_statement, validate_contract

# Apify SDK
from apify import Actor

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("apify-document-to-json")

# ── Configuration ──────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "eng+ita+spa")
MAX_FILE_SIZE_MB = 20

# ── Prompts and Schemas ────────────────────────────────────────────
PROMPTS = {
    "invoice": INVOICE_SYSTEM_PROMPT,
    "bank_statement": BANK_STATEMENT_SYSTEM_PROMPT,
    "contract": CONTRACT_SYSTEM_PROMPT,
    "generic": GENERIC_SYSTEM_PROMPT,
}

VALIDATORS = {
    "invoice": validate_invoice,
    "bank_statement": validate_bank_statement,
    "contract": validate_contract,
}

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
            },
        },
        "seller": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "vat_id": {"type": "string"},
                "address": {"type": "string"},
            },
        },
        "buyer": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "vat_id": {"type": "string"},
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
                "statement_period": {"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"}}},
                "currency": {"type": "string"},
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
    },
}

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["contract"]},
        "confidence": {"type": "number"},
        "metadata": {"type": "object", "properties": {
            "title": {"type": "string"},
            "contract_date": {"type": "string"},
            "language": {"type": "string"},
        }},
        "parties": {
            "type": "array",
            "items": {"type": "object", "properties": {
                "name": {"type": "string"},
                "role": {"type": "string"},
                "vat_id": {"type": "string"},
            }},
        },
        "dates": {"type": "object", "properties": {
            "effective_date": {"type": "string"},
            "expiry_date": {"type": "string"},
            "renewal_terms": {"type": "string"},
        }},
        "financial_terms": {"type": "object", "properties": {
            "fee": {"type": "number"},
            "currency": {"type": "string"},
            "payment_terms": {"type": "string"},
            "late_payment_penalty": {"type": "string"},
        }},
        "key_clauses": {
            "type": "array",
            "items": {"type": "object", "properties": {
                "clause_number": {"type": ["integer", "string"]},
                "title": {"type": "string"},
                "summary": {"type": "string"},
            }},
        },
    },
}

GENERIC_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["report", "letter", "memo", "article", "manual", "other"]},
        "confidence": {"type": "number"},
        "title": {"type": "string"},
        "text_content": {"type": "string"},
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                },
            },
        },
    },
}

SCHEMAS = {
    "invoice": INVOICE_SCHEMA,
    "bank_statement": BANK_STATEMENT_SCHEMA,
    "contract": CONTRACT_SCHEMA,
    "generic": GENERIC_SCHEMA,
}

# PE (Pay-Per-Event) event names for Apify charging
EVENT_NAMES = {
    "invoice": "invoice-parsed",
    "bank_statement": "bank-statement-parsed",
    "contract": "contract-parsed",
    "generic": "generic-parsed",
}

PRICES = {
    "invoice": 0.01,
    "bank_statement": 0.015,
    "contract": 0.02,
    "generic": 0.0,
}


async def main():
    """Main entrypoint for Apify Actor."""
    await Actor.init()

    # ── Validate API key ───────────────────────────────────────
    if not DEEPSEEK_API_KEY:
        await _push_error("missing_config", "DEEPSEEK_API_KEY environment variable is not set. Add it in Actor settings → Environment variables.")
        await Actor.exit()
        return

    # ── Read input ─────────────────────────────────────────────
    user_input = await Actor.get_input() or {}
    file_url = user_input.get("file_url", "").strip()
    doc_type = user_input.get("document_type", "invoice")
    language = user_input.get("language", DEFAULT_LANGUAGE)
    validate = user_input.get("validate_totals", False)

    # ── Validate input ─────────────────────────────────────────
    if not file_url:
        await _push_error("missing_parameter", "file_url is required. Provide a public URL to a PDF file.")
        await Actor.exit()
        return

    if doc_type not in PROMPTS:
        await _push_error("invalid_parameter", f"Invalid document_type: '{doc_type}'. Valid values: invoice, bank_statement, contract, generic.")
        await Actor.exit()
        return

    logger.info(f"Processing: type={doc_type}, url={file_url[:80]}, lang={language}, validate={validate}")

    try:
        # ── Step 1: Download PDF ───────────────────────────────
        logger.info("Downloading PDF...")
        extractor = PDFExtractor()
        pdf_bytes = await extractor.download_pdf(file_url)

        # ── Step 2: Extract text (with OCR if needed) ──────────
        logger.info("Extracting text from PDF...")
        text, used_ocr = extractor.extract_text(pdf_bytes, ocr_language=language)

        if not text.strip():
            await _push_error("empty_document", "No text could be extracted from this PDF. The file may be empty, corrupted, or password-protected.")
            await Actor.exit()
            return

        # ── Step 3: Call DeepSeek ──────────────────────────────
        logger.info(f"Calling DeepSeek ({doc_type})...")
        prompt = PROMPTS[doc_type]
        schema = SCHEMAS[doc_type]
        if used_ocr:
            prompt += "\n\nNOTE: This document was processed with OCR. Be careful with number recognition."

        client = DeepSeekClient(
            api_key=DEEPSEEK_API_KEY,
            model=DEEPSEEK_MODEL,
        )

        try:
            result = await client.extract_structured(
                text=text,
                system_prompt=prompt,
                output_schema=schema,
            )
        finally:
            await client.close()

        # ── Step 4: Validation ─────────────────────────────────
        if validate and doc_type in VALIDATORS:
            try:
                validator = VALIDATORS[doc_type]
                warnings = validator(result)
                if warnings:
                    result["validation_warnings"] = warnings
                    logger.info(f"Validation warnings: {warnings}")
            except Exception as e:
                logger.warning(f"Validation error: {e}")

        result["used_ocr"] = used_ocr

        # ── Step 5: Charge for document type ───────────────────
        event_name = EVENT_NAMES[doc_type]
        try:
            charge_result = await Actor.charge(event_name=event_name, count=1)
            logger.info(f"Charged: {event_name}")
        except Exception as e:
            logger.warning(f"Charge failed for {event_name}: {e}")

        # ── Step 6: Push result ────────────────────────────────
        await Actor.push_data({
            "success": True,
            "data": result
        })

        logger.info("✅ Processing complete")

    except Exception as e:
        logger.exception("Processing failed")
        await _push_error("processing_error", str(e))

    await Actor.exit()


async def _push_error(error_code: str, message: str):
    """Push an error result to the dataset."""
    logger.error(f"Error [{error_code}]: {message}")
    await Actor.push_data({
        "success": False,
        "error": error_code,
        "message": message
    })


if __name__ == "__main__":
    asyncio.run(main())
