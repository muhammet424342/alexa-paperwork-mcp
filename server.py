import os
import json
import requests
from mcp.server.fastmcp import FastMCP
from store import (
    init_db,
    add_document as store_add_document,
    list_due as store_list_due,
    get_document as store_get_document,
    mark_paid as store_mark_paid,
    monthly_total as store_monthly_total,
)

FIELDCAST_URL = os.environ.get("FIELDCAST_URL", "http://127.0.0.1:8010/v1/extract")
FIELDCAST_KEY = os.environ.get("FIELDCAST_KEY", "demo_key_public")

mcp = FastMCP("paperwork-pal")


def extract_fields(text: str) -> dict:
    """Call Fieldcast extraction API to get structured fields from document text."""
    try:
        resp = requests.post(
            FIELDCAST_URL,
            headers={"X-API-Key": FIELDCAST_KEY, "Content-Type": "application/json"},
            json={"text": text, "fields": ["vendor", "amount", "currency", "due_date"]},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "vendor": data.get("vendor"),
            "amount": data.get("amount"),
            "currency": data.get("currency"),
            "due_date": data.get("due_date"),
        }
    except Exception:
        return {"vendor": None, "amount": None, "currency": None, "due_date": None}


@mcp.tool()
def add_document(text: str, kind: str = "bill") -> dict:
    """Add a document (bill/receipt) from text. Extracts vendor, amount, currency, due_date via Fieldcast and stores it. Returns the stored record."""
    fields = extract_fields(text)
    record = store_add_document(
        kind=kind,
        vendor=fields["vendor"],
        amount=fields["amount"],
        currency=fields["currency"],
        due_date=fields["due_date"],
        raw_text=text,
    )
    return record


@mcp.tool()
def list_due(days: int = 7) -> list:
    """List unpaid documents due within the next N days (default 7), sorted by due date."""
    return store_list_due(days)


@mcp.tool()
def get_document(vendor: str) -> dict:
    """Get the most recent document for a vendor (case-insensitive, partial match)."""
    result = store_get_document(vendor)
    return result if result else {}


@mcp.tool()
def mark_paid(document_id: int) -> dict:
    """Mark a document as paid by its ID."""
    ok = store_mark_paid(document_id)
    return {"success": ok, "document_id": document_id}


@mcp.tool()
def monthly_total(month: str = "") -> dict:
    """Get total amounts per currency for a month (YYYY-MM, empty = current month)."""
    return store_monthly_total(month)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8765"))
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.settings.streamable_http_path = "/mcp"
    mcp.run(transport="streamable-http")