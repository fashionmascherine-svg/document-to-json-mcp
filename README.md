# Document-to-JSON Converter

> **Turn PDFs into structured JSON in seconds. AI-powered, no coding needed.**

![MCP Server](https://img.shields.io/badge/MCP-Server-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Apify](https://img.shields.io/badge/Apify-Actor-green)

---

## 🚀 What does it do?

Paste a PDF URL → get structured JSON. That's it.

Perfect for:
- **Accountants** — extract invoice data (numbers, dates, totals, VAT, IBAN)
- **Developers** — automate document processing in your apps
- **Business analysts** — convert bank statements to spreadsheets
- **Legal teams** — extract contract clauses and dates automatically

## 📋 Supported documents

| Type | What you get | Price |
|---|---|---|
| **Invoice** | Seller, buyer, line items, totals, VAT, IBAN, payment info | $0.01 |
| **Bank Statement** | All transactions, balances, fees, account holder | $0.015 |
| **Contract** | Parties, key clauses, dates, financial terms, jurisdiction | $0.02 |
| **Generic** | Full text + tables from any document | **Free during launch** |

## ✨ Example output

```json
{
  "success": true,
  "data": {
    "document_type": "invoice",
    "confidence": 0.97,
    "metadata": {
      "invoice_number": "INV-2024-00123",
      "invoice_date": "2024-03-15",
      "currency": "EUR"
    },
    "seller": {
      "name": "Acme S.p.A.",
      "vat_id": "IT01234567890"
    },
    "line_items": [
      {
        "description": "Consulting services",
        "quantity": 1,
        "unit_price": 5000.00,
        "net_amount": 5000.00,
        "vat_rate": 22.0,
        "total": 6100.00
      }
    ],
    "totals": {
      "net_total": 5000.00,
      "vat_total": 1100.00,
      "grand_total": 6100.00
    },
    "payment_info": {
      "iban": "IT60X0542811101000000123456"
    }
  }
}
```

## 🎯 Why this Actor?

| Feature | Benefit |
|---|---|
| **Multi-language** | English, Italian, Spanish (OCR) |
| **OCR included** | Works with scanned documents too |
| **Validation** | Auto-checks totals and dates for accuracy |
| **Pay per use** | No subscription, pay only for what you process |

## 🔧 How to use

1. **Get a public PDF URL** (Dropbox, Google Drive, your server)
2. **Select the document type**
3. **Run the Actor**
4. **Get your JSON** in seconds

That's it. No configuration, no API keys needed.

## 💰 Pricing

| Document type | Price |
|---|---|
| Invoice | **$0.01** ($10/1000) |
| Bank statement | **$0.015** ($15/1000) |
| Contract | **$0.02** ($20/1000) |
| Generic | **Free during launch** |

*Pay-per-event via Apify. Pay only for successful extractions. No subscription, no hidden fees.*

## 🔒 Privacy

- PDFs are processed and **not stored** after extraction
- Data is available in your private dataset
- All API keys stay encrypted

## 📚 Supported OCR languages

`eng` (English), `ita` (Italian), `spa` (Spanish)

Combine with `+` for multi-language scanned documents: `eng+ita+spa` (default)

## 🤖 Built for AI agents (MCP)

This Actor is an **MCP server**: AI agents can call it directly as a tool to turn any
PDF into JSON, with zero configuration — just pass a public `file_url`. Specialized
tools (`parse_invoice`, `parse_bank_statement`, `parse_contract`) and a free
`parse_generic_document` make it easy for an LLM to pick the right one for the task.
