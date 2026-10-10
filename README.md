# Paperwork Pal — Alexa+ Document Assistant

An MCP server that lets Alexa+ answer questions about your household bills and receipts.

## What it does

Send the text of a bill or receipt and Alexa+ can answer:
- "What bills are due this week?"
- "How much is my electric bill and when is it due?"
- "How much did I pay in total this month?"

The server extracts structured fields (vendor, amount, currency, due date) from document text using the Fieldcast extraction API, stores them in SQLite, and exposes tools via MCP (Model Context Protocol) over Streamable HTTP.

## Live demo

- MCP endpoint (Streamable HTTP, spec 2025-11-25): `https://paperwork.157-173-122-86.sslip.io/mcp`
- Any MCP client can connect, e.g. MCP Inspector: `npx @modelcontextprotocol/inspector` → transport *Streamable HTTP* → the URL above.
- If a field is not written in the document, extraction returns `null` — the server never guesses a vendor, amount or due date.

## Requirements

- Python 3.10+
- Fieldcast extraction API running at `http://127.0.0.1:8010/v1/extract` (or set `FIELDCAST_URL`)
- MCP-compatible client (Alexa+ with MCP support)

## Installation

```bash
pip install --user --break-system-packages -r requirements.txt
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPERWORK_DB` | `./paperwork.db` | SQLite database path |
| `FIELDCAST_URL` | `http://127.0.0.1:8010/v1/extract` | Fieldcast extraction endpoint |
| `FIELDCAST_KEY` | `demo_key_public` | API key for Fieldcast (X-API-Key header) |
| `PORT` | `8765` | Server port |

## Running

```bash
python server.py
```

Server starts on `0.0.0.0:8765` at path `/mcp` using Streamable HTTP transport (MCP spec 2025-11-25+).

## Connecting to Alexa+

In the Alexa+ developer console, add an MCP server with:
- **Transport**: Streamable HTTP
- **URL**: `http://<your-host>:8765/mcp`

## Example conversation

**User**: "Add my electric bill — Acme Energy, $142.50, due October 20."
**Alexa+**: (calls `add_document`) "Saved. Your Acme Energy bill for $142.50 is due 2026-10-20."

**User**: "What bills are due this week?"
**Alexa+**: (calls `list_due`) "You have 2 bills due: Acme Energy ($142.50) due Oct 20, and WaterCo ($45.00) due Oct 22."

**User**: "How much did I pay this month?"
**Alexa+**: (calls `monthly_total`) "In October you paid $320.50 across 3 bills."

## Tools

| Tool | Description |
|------|-------------|
| `add_document(text, kind?)` | Extract fields from text and store document |
| `list_due(days?)` | Unpaid documents due within N days (default 7) |
| `get_document(vendor)` | Most recent document for vendor (partial, case-insensitive) |
| `mark_paid(document_id)` | Mark document as paid |
| `monthly_total(month?)` | Totals per currency for YYYY-MM (default current month) |

## Testing

```bash
pytest tests/
```

Tests use a temporary SQLite database and mock the Fieldcast API — no network required.

## License

MIT — see [LICENSE](LICENSE).