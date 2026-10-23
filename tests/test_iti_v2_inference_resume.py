"""Retomada de inferência ITI-v2: identidade completa da predição."""

from modules.experiment.campaign.iti_v2_inference import (
    prediction_identity_tuple,
    stored_row_identity,
)


def test_stored_row_identity_matches_expected_fields() -> None:
    row = {
        "news_id": "n1",
        "view_id": "entity_context_v1",
        "article_version_id": "v2",
        "view_hash": "abc",
        "model_key": "finbert_ptbr",
        "model_revision_sha": "sha1",
        "company_id": "Sabesp",
        "date": "2024-01-01",
        "text_max_length": 512,
    }
    expected = prediction_identity_tuple(
        news_id="n1",
        view_id="entity_context_v1",
        article_version_id="v2",
        view_hash="abc",
        model_key="finbert_ptbr",
        model_revision_sha="sha1",
        company_id="Sabesp",
        date="2024-01-01",
        max_length=512,
    )
    assert stored_row_identity(row) == expected


def test_stale_view_hash_must_not_match() -> None:
    row = {
        "news_id": "n1",
        "view_id": "entity_context_v1",
        "article_version_id": "v1",
        "view_hash": "old",
        "model_key": "finbert_ptbr",
        "model_revision_sha": "sha1",
    }
    expected = prediction_identity_tuple(
        news_id="n1",
        view_id="entity_context_v1",
        article_version_id="v2",
        view_hash="new",
        model_key="finbert_ptbr",
        model_revision_sha="sha1",
        company_id="Sabesp",
        date="2024-01-01",
        max_length=512,
    )
    assert stored_row_identity(row) != expected
