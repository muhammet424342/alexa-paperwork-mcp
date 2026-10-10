import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import store
import server


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("PAPERWORK_DB", str(db_file))
    store.init_db()
    yield
    if db_file.exists():
        db_file.unlink()


def mock_fieldcast_response(vendor="Acme Corp", amount=123.45, currency="USD", due_date="2026-10-15"):
    def mock_post(url, headers, json, timeout):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = {"data": {
            "vendor": vendor,
            "amount": amount,
            "currency": currency,
            "due_date": due_date
        }}
        return mock_resp
    return mock_post


def test_add_document_saves_and_preserves_nulls(monkeypatch):
    monkeypatch.setattr("requests.post", mock_fieldcast_response(
        vendor=None, amount=None, currency=None, due_date=None
    ))

    result = server.add_document("Some random text", "receipt")
    assert result["kind"] == "receipt"
    assert result["vendor"] is None
    assert result["amount"] is None
    assert result["currency"] is None
    assert result["due_date"] is None
    assert result["raw_text"] == "Some random text"
    assert result["paid"] == 0


def test_add_document_with_extracted_fields(monkeypatch):
    monkeypatch.setattr("requests.post", mock_fieldcast_response())

    result = server.add_document("Invoice from Acme Corp for $123.45 due 2026-10-15")
    assert result["vendor"] == "Acme Corp"
    assert result["amount"] == 123.45
    assert result["currency"] == "USD"
    assert result["due_date"] == "2026-10-15"


def test_list_due_filters_by_date_and_sort(monkeypatch):
    monkeypatch.setattr("requests.post", mock_fieldcast_response(
        vendor="Test Vendor", amount=100.0, currency="USD", due_date="2026-12-31"
    ))

    store.add_document("bill", "Vendor A", 100.0, "USD", "2026-10-12", "text1")
    store.add_document("bill", "Vendor B", 200.0, "USD", "2026-10-20", "text2")
    store.add_document("bill", "Vendor C", 300.0, "USD", "2026-10-10", "text3")
    store.add_document("bill", "Vendor D", 400.0, "USD", "2026-10-15", "text4")

    store.mark_paid(3)

    due = server.list_due(days=7)
    assert len(due) == 2
    assert due[0]["vendor"] == "Vendor A"
    assert due[1]["vendor"] == "Vendor D"
    assert due[0]["due_date"] == "2026-10-12"
    assert due[1]["due_date"] == "2026-10-15"


def test_get_document_partial_case_insensitive_match(monkeypatch):
    monkeypatch.setattr("requests.post", mock_fieldcast_response(
        vendor="Test", amount=1.0, currency="USD", due_date="2026-12-31"
    ))

    store.add_document("bill", "Acme Corporation", 100.0, "USD", "2026-10-15", "text1")
    store.add_document("bill", "Acme Corp", 200.0, "USD", "2026-10-20", "text2")

    result = server.get_document("acme corp")
    assert result["vendor"] == "Acme Corp"
    assert result["amount"] == 200.0


def test_mark_paid_removes_from_list_due(monkeypatch):
    monkeypatch.setattr("requests.post", mock_fieldcast_response(
        vendor="Test", amount=1.0, currency="USD", due_date="2026-12-31"
    ))

    store.add_document("bill", "Vendor X", 50.0, "USD", "2026-10-15", "text")
    doc = store.get_document("Vendor X")
    assert doc is not None

    result = server.mark_paid(doc["id"])
    assert result["success"] is True

    due = server.list_due(days=30)
    assert len(due) == 0


def test_monthly_total_groups_by_currency(monkeypatch):
    monkeypatch.setattr("requests.post", mock_fieldcast_response(
        vendor="Test", amount=1.0, currency="USD", due_date="2026-12-31"
    ))

    store.add_document("bill", "V1", 100.0, "USD", "2026-10-15", "t1")
    store.add_document("bill", "V2", 200.0, "USD", "2026-10-20", "t2")
    store.add_document("bill", "V3", 50.0, "EUR", "2026-10-25", "t3")

    totals = server.monthly_total("2026-10")
    assert totals.get("USD") == 300.0
    assert totals.get("EUR") == 50.0


def test_all_five_tools_registered():
    tool_names = set(server.mcp._tool_manager._tools.keys())
    expected = {"add_document", "list_due", "get_document", "mark_paid", "monthly_total"}
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"