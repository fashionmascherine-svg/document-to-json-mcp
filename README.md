# Document-to-JSON MCP Server

> Converte PDF in JSON strutturato. Supporta fatture, estratti conto, contratti e documenti generici.
> Paghi per chiamata via **x402 USDC su Base** — niente subscription, niente Stripe.

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![x402 Payments](https://img.shields.io/badge/Payments-x402_USDC-green)](https://www.x402.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Quick Start

### 1. Configura il client MCP

#### Claude Desktop

```json
{
  "mcpServers": {
    "document-to-json": {
      "url": "https://glama.ai/endpoints/document-to-json/mcp",
      "env": {
        "X402_WALLET": "0xYourWalletAddress",
        "X402_NETWORK": "eip155:8453"
      }
    }
  }
}
```

#### Cursor

```json
{
  "mcpServers": {
    "document-to-json": {
      "url": "https://glama.ai/endpoints/document-to-json/mcp",
      "headers": {
        "X402-Wallet": "0xYourWalletAddress"
      }
    }
  }
}
```

### 2. Chiama un tool

```
"Estrai i dati da questa fattura: https://example.com/fattura.pdf"
```

Il server processa il PDF e restituisce JSON strutturato. Paghi solo per le chiamate effettuate.

---

## 🛠️ Tools

| Tool | Prezzo | Descrizione |
|---|---|---|
| `parse_invoice` | $0.02 | Estrai dati strutturati da fatture (seller, buyer, line items, totals, IBAN) |
| `parse_bank_statement` | $0.03 | Estrai transazioni e saldi da estratti conto |
| `parse_contract` | $0.05 | Estrai clausole, parti, date e termini finanziari da contratti |
| `parse_generic_document` | $0.01 | Estrai testo e tabelle da qualsiasi PDF |
| `supported_document_types` | **Gratis** | Lista dei tipi documento supportati |

### Example: `parse_invoice`

**Input:**
```json
{
  "file_url": "https://example.com/fattura-2024-001.pdf",
  "validate_totals": true
}
```

**Output:**
```json
{
  "success": true,
  "data": {
    "document_type": "invoice",
    "confidence": 0.97,
    "metadata": {
      "invoice_number": "INV-2024-00123",
      "invoice_date": "2024-03-15",
      "due_date": "2024-04-14",
      "currency": "EUR"
    },
    "seller": {
      "name": "Acme S.p.A.",
      "vat_id": "IT01234567890",
      "address": "Via Roma 123, 20100 Milano"
    },
    "buyer": {
      "name": "Client S.r.l.",
      "vat_id": "IT09876543210"
    },
    "line_items": [
      {
        "description": "Consulenza sviluppo software",
        "quantity": 1,
        "unit_price": 5000.0,
        "net_amount": 5000.0,
        "vat_rate": 22.0,
        "vat_amount": 1100.0,
        "total": 6100.0
      }
    ],
    "totals": {
      "net_total": 5000.0,
      "vat_total": 1100.0,
      "grand_total": 6100.0
    },
    "payment_info": {
      "iban": "IT60X0542811101000000123456",
      "bank_name": "Intesa Sanpaolo",
      "payment_terms": "Bonifico 30 giorni"
    }
  }
}
```

---

## 💰 Pricing

### Pay-per-call via x402 (USDC su Base)

| Tool | Prezzo | Free tier |
|---|---|---|
| `supported_document_types` | **Gratis** | ∞ |
| `parse_invoice` | **$0.02** | 3/giorno |
| `parse_bank_statement` | **$0.03** | 3/giorno |
| `parse_contract` | **$0.05** | 1/giorno |
| `parse_generic_document` | **$0.01** | 5/giorno |

**Niente subscription. Niente abbonamento. Paghi solo quando usi.**

Perché DeepSeek-v4-flash è molto economico, riusciamo a offrire prezzi 5-10x inferiori alle API concorrenti (Nanonets, AWS Textract, GPT-4o).

---

## 🏗️ Architettura

```
PDF URL → Download → Text Extraction (PyMuPDF/OCR)
         → DeepSeek-v4-flash → Structured JSON → Response
         → Validation Layer → Warning flags
```

- **PDF Processing**: PyMuPDF per PDF nativi, Tesseract OCR per documenti scannerizzati
- **AI Extraction**: DeepSeek-v4-flash con function calling per output JSON garantito
- **Validation**: Controllo automatico di somme, date e formati
- **Payments**: x402 protocol — pagamenti diretti USDC su Base, nessun intermediario

---

## 🤔 Perché DeepSeek-v4-flash?

| Modello | Costo per documento | Accuratezza |
|---|---|---|
| **DeepSeek-v4-flash** (questo server) | **~$0.0005** | ✅ Alta |
| GPT-4o-mini | ~$0.002 | ✅ Alta |
| Claude 3.5 Haiku | ~$0.003 | ✅ Alta |
| GPT-4o | ~$0.03 | ✅ Molto alta |

DeepSeek-v4-flash è **50-100x più economico** dei modelli premium, permettendoti di processare documenti a prezzi bassissimi con margini eccellenti.

---

## 👨‍💻 Sviluppo

### Setup

```bash
git clone https://github.com/tuo-org/document-to-json-mcp
cd document-to-json-mcp

# Crea file env
cp .env.example .env
# Modifica .env con la tua DeepSeek API key e wallet USDC

# Installa dipendenze
pip install -r requirements.txt

# Avvia server
python -m src.server
```

### Test

```bash
pytest tests/
```

### Dipendenze

- `mcp` — Model Context Protocol SDK
- `paymcp` — Payment layer with x402 support
- `fastmcp` — Fast MCP server framework
- `PyMuPDF` — PDF text extraction
- `pdf2image` + `pytesseract` — OCR per documenti scannerizzati
- `httpx` — HTTP client per download PDF e API DeepSeek
- `python-dotenv` — Configurazione ambiente

---

## 📦 Distribuzione

Questo MCP server è disponibile su:

- **[Glama.ai](https://glama.ai/mcp/servers)** — Hosting + directory
- **[Smithery.ai](https://smithery.ai/servers)** — Registry + hosting
- **[MCP Registry](https://registry.modelcontextprotocol.io)** — Directory ufficiale
- **Apify Store** — Pay-per-event pricing (per utenti Apify)

---

## 📄 Licenza

MIT

---

## 🔗 Link Utili

- [MCP Protocol Documentation](https://modelcontextprotocol.io)
- [x402 Payment Protocol](https://www.x402.org)
- [DeepSeek API](https://platform.deepseek.com)
- [PayMCP SDK](https://github.com/PayMCP/paymcp)
- [Base Network](https://base.org)
