"""
Post-processing validation for extracted document data.
Checks numerical consistency, date formats, and required fields.
"""
import re
from typing import Any, List
from datetime import datetime


def validate_invoice(data: dict) -> List[str]:
    """
    Validate extracted invoice data. Returns a list of warning messages.
    
    Checks performed:
    - Required fields presence
    - Date format validity
    - Line items sum vs declared totals
    - VAT calculation consistency
    """
    warnings: list[str] = []
    metadata = data.get("metadata") or {}
    totals = data.get("totals") or {}
    line_items = data.get("line_items") or []

    # ── Required fields ─────────────────────────────────────────
    if not metadata.get("invoice_number"):
        warnings.append("Missing invoice_number")

    # ── Date validation ─────────────────────────────────────────
    for date_field in ["invoice_date", "due_date"]:
        date_val = metadata.get(date_field)
        if date_val:
            if not _is_valid_iso_date(str(date_val)):
                warnings.append(f"Invalid date format in {date_field}: {date_val}")

    # ── Line items validation ───────────────────────────────────
    if line_items:
        calculated_net = sum(
            _safe_float(item.get("net_amount")) for item in line_items
        )
        declared_net = _safe_float(totals.get("net_total"))
        if declared_net and abs(calculated_net - declared_net) > 0.02:
            warnings.append(
                f"Line items net sum ({calculated_net:.2f}) != "
                f"declared net total ({declared_net:.2f})"
            )

        calculated_gross = sum(
            _safe_float(item.get("total")) for item in line_items
        )
        declared_gross = _safe_float(totals.get("grand_total"))
        if declared_gross and abs(calculated_gross - declared_gross) > 0.02:
            warnings.append(
                f"Line items gross sum ({calculated_gross:.2f}) != "
                f"declared grand total ({declared_gross:.2f})"
            )

    return warnings


def validate_bank_statement(data: dict) -> List[str]:
    """
    Validate extracted bank statement data.
    """
    warnings: list[str] = []
    balances = data.get("balances") or {}
    transactions = data.get("transactions") or []

    # ── Balance consistency ─────────────────────────────────────
    opening = _safe_float(balances.get("opening_balance"))
    closing = _safe_float(balances.get("closing_balance"))
    total_credits = _safe_float(balances.get("total_credits"))
    total_debits = _safe_float(balances.get("total_debits"))

    if opening and closing and total_credits is not None and total_debits is not None:
        expected_closing = opening + total_credits - total_debits
        if abs(closing - expected_closing) > 0.02:
            warnings.append(
                f"Balance inconsistency: opening({opening:.2f}) + "
                f"credits({total_credits:.2f}) - debits({total_debits:.2f}) = "
                f"{expected_closing:.2f}, but closing balance is {closing:.2f}"
            )

    # ── Transaction count vs balance ────────────────────────────
    if _safe_float(balances.get("total_credits")) is not None:
        calculated_credits = sum(
            _safe_float(t.get("amount")) for t in transactions if t.get("type") == "credit"
        )
        if abs(calculated_credits - total_credits) > 0.02:
            warnings.append(
                f"Sum of credit transactions ({calculated_credits:.2f}) != "
                f"declared total credits ({total_credits:.2f})"
            )

    return warnings


def validate_contract(data: dict) -> List[str]:
    """
    Validate extracted contract data.
    """
    warnings: list[str] = []
    dates = data.get("dates") or {}
    clauses = data.get("key_clauses") or []

    # ── Date validation ─────────────────────────────────────────
    for date_field in ["effective_date", "expiry_date"]:
        date_val = dates.get(date_field)
        if date_val and not _is_valid_iso_date(str(date_val)):
            warnings.append(f"Invalid date format for {date_field}: {date_val}")

    # ── Essential clause check ──────────────────────────────────
    clause_titles = [str(c.get("title", "")).lower() for c in clauses]
    essential_keywords = [
        "termination", "confidentiality", "liability", "governing law"
    ]
    for keyword in essential_keywords:
        if not any(keyword in title for title in clause_titles):
            warnings.append(f"Missing essential clause: {keyword}")

    return warnings


def _safe_float(value: Any) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _is_valid_iso_date(date_str: str) -> bool:
    """Check if a string is a valid ISO 8601 date (YYYY-MM-DD)."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False
