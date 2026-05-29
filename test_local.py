"""
Test script: parse a local PDF invoice using the server's internal pipeline.
No URL needed — reads the file directly from your PC.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.extractors.pdf import PDFExtractor
from src.llm.deepseek import DeepSeekClient
from src.llm.prompts import INVOICE_SYSTEM_PROMPT, BANK_STATEMENT_SYSTEM_PROMPT, CONTRACT_SYSTEM_PROMPT, GENERIC_SYSTEM_PROMPT
from src.validation import validate_invoice

# ─── CONFIG ─────────────────────────────────────────────────────────
# Metti i tuoi PDF qui:
INVOICES_DIR = Path("tests/sample_invoices")

# In quali lingue hai le fatture?
INVOICES = {
    "italiano": [
        "fattura-italiana.pdf",
        # Aggiungi qui i nomi dei tuoi file
    ],
    "spagnolo": [
        "factura-espanola.pdf",
        # Aggiungi qui
    ],
    "inglese": [
        "invoice-english.pdf",
        # Aggiungi qui
    ],
}

# ─── TEST ───────────────────────────────────────────────────────────

async def test_invoice(file_path: Path, language: str, label: str):
    """Test parse_invoice su un file locale."""
    print(f"\n{'='*60}")
    print(f"📄 TEST: {label}")
    print(f"📁 File: {file_path.name}")
    print(f"{'='*60}")
    
    try:
        # 1. Leggi il file
        pdf_bytes = file_path.read_bytes()
        print(f"   ✅ Letto {len(pdf_bytes)} bytes")
        
        # 2. Estrai testo
        extractor = PDFExtractor()
        text, used_ocr = extractor.extract_text(pdf_bytes)
        print(f"   ✅ Testo estratto ({'OCR' if used_ocr else 'nativo'}): {len(text)} caratteri")
        if text:
            print(f"   📝 Anteprima: {text[:200]}...")
        
        # 3. Chiama DeepSeek
        client = DeepSeekClient()
        
        # Schema per fattura
        schema = {
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
        
        prompt = INVOICE_SYSTEM_PROMPT
        if used_ocr:
            prompt += "\n\nNOTE: OCR processed. Be careful with numbers."
        
        result = await client.extract_structured(
            text=text,
            system_prompt=prompt,
            output_schema=schema,
        )
        
        # 4. Validazione
        warnings = validate_invoice(result)
        
        # 5. Output
        print(f"\n   📊 RISULTATO:")
        print(f"   Confidenza: {result.get('confidence', 'N/A')}")
        
        meta = result.get('metadata', {})
        if meta.get('invoice_number'):
            print(f"   🏷️  Fattura n.: {meta['invoice_number']}")
            print(f"   📅 Data: {meta.get('invoice_date', 'N/A')}")
            print(f"   💰 Valuta: {meta.get('currency', 'N/A')}")
        
        seller = result.get('seller', {})
        if seller.get('name'):
            print(f"   🏢 Venditore: {seller['name']}")
            print(f"   🆔 Partita IVA: {seller.get('vat_id', 'N/A')}")
        
        buyer = result.get('buyer', {})
        if buyer.get('name'):
            print(f"   👤 Compratore: {buyer['name']}")
        
        totals = result.get('totals', {})
        if totals.get('grand_total'):
            print(f"   💵 Totale: {totals['grand_total']} {meta.get('currency', '')}")
        if totals.get('net_total'):
            print(f"   📊 Imponibile: {totals['net_total']}")
        if totals.get('vat_total'):
            print(f"   🧾 IVA: {totals['vat_total']}")
        
        items = result.get('line_items', [])
        if items:
            print(f"   📋 Line items: {len(items)}")
            for item in items[:3]:  # mostra prime 3
                print(f"      - {item.get('description', '')[:50]}: {item.get('total', '')}")
            if len(items) > 3:
                print(f"      ... e altre {len(items)-3}")
        
        pay = result.get('payment_info', {})
        if pay.get('iban'):
            print(f"   🏦 IBAN: {pay['iban']}")
            print(f"   🏛️  Banca: {pay.get('bank_name', 'N/A')}")
        
        if warnings:
            print(f"\n   ⚠️  WARNINGS:")
            for w in warnings:
                print(f"      ⚠️  {w}")
        
        print(f"\n   ✅ TEST COMPLETATO CON SUCCESSO!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'client' in dir():
            await client.close()


async def main():
    print("📑 DOCUMENT-TO-JSON MCP — TEST LOCALE")
    print("="*60)
    print("\n📂 Cerca PDF in:", INVOICES_DIR.resolve())
    print()
    
    # Controlla se la cartella esiste e ha file
    if not INVOICES_DIR.exists():
        print("❌ Cartella non trovata:", INVOICES_DIR)
        print("📁 Crealo e mettici i tuoi PDF:")
        print(f"   {INVOICES_DIR.resolve()}")
        return
    
    pdf_files = list(INVOICES_DIR.glob("*.pdf"))
    if not pdf_files:
        print("❌ Nessun PDF trovato in:", INVOICES_DIR)
        print("📁 Copia i tuoi file PDF qui:")
        print(f"   {INVOICES_DIR.resolve()}")
        print("\n   Poi esegui:")
        print(f"   cd {Path(__file__).resolve().parent}")
        print("   . venv/bin/activate")
        print("   python test_local.py")
        return
    
    print(f"✅ Trovati {len(pdf_files)} PDF:")
    for f in pdf_files:
        print(f"   📄 {f.name} ({f.stat().st_size / 1024:.0f} KB)")
    
    # Testa ogni PDF
    success_count = 0
    for pdf_file in pdf_files:
        ok = await test_invoice(pdf_file, "auto", pdf_file.stem)
        if ok:
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"📊 RIEPILOGO: {success_count}/{len(pdf_files)} test superati")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
