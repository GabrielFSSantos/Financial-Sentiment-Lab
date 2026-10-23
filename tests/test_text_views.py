"""Testes de contexto focal (P03/P08)."""

from modules.datasets.text_views import build_document_view, build_entity_context_view


def test_multi_company_different_contexts():
    body = (
        "A Sabesp anunciou investimentos. "
        "A Copasa registrou perdas no trimestre."
    )
    sab = build_entity_context_view("Título", body, "sabesp")
    cop = build_entity_context_view("Título", body, "copasa")
    assert sab.text != cop.text
    assert "Sabesp" in sab.text or "sabesp" in sab.text.lower()
    assert "Copasa" in cop.text or "copasa" in cop.text.lower()


def test_not_evaluable_without_alias():
    result = build_entity_context_view("T", "Mercado fecha em alta.", "sabesp")
    assert result.status == "not_evaluable"
    assert not result.target_visible


def test_document_view_ok():
    doc = build_document_view("A", "Corpo.")
    assert doc.view_id == "document_v1"
    assert doc.status == "ok"
