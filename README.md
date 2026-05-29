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
| **Invoice** | Seller, buyer, line items, totals, VAT, IBAN, payment info | $0.02 |
| **Bank Statement** | All transactions, balances, fees, account holder | $0.03 |
| **Contract** | Parties, key clauses, dates, financial terms, jurisdiction | $0.05 |
| **Generic** | Full text + tables from any document | $0.01 |

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
| **Multi-language** | Italian, English, Spanish, German, French, Portuguese |
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
| Invoice | **$0.02** ($20/1000) |
| Bank statement | **$0.03** ($30/1000) |
| Contract | **$0.05** ($50/1000) |
| Generic | **$0.01** ($10/1000) |

*Pay only for successful extractions. No hidden fees.*

## 🔒 Privacy

- PDFs are processed and **not stored** after extraction
- Data is available in your private dataset
- All API keys stay encrypted

## 📚 Supported languages

`ita` (Italian), `eng` (English), `spa` (Spanish), `fra` (French), `deu` (German), `por` (Portuguese)

Combine with `+` for multi-language documents: `ita+eng+spa`
