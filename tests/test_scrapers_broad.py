"""Testes de modo broad e corpus pendente."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from modules.scrapers.core.search import SearchHit
from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.pipeline.corpus import build_merged_corpus
from modules.scrapers.schema.entities import PENDING_COMPANY
from modules.scrapers.sites.base import SiteScraper


def test_broad_mode_saves_pending_sector_article(project_root, tmp_path: Path) -> None:
    configuration = load_scrapers_configuration(project_root=project_root)
    defaults = dict(configuration.defaults)
    defaults["collection_mode"] = "broad"
    configuration = configuration.__class__(
        project_root=configuration.project_root,
        defaults=defaults,
        sites=configuration.sites,
    )
    site = next(site for site in configuration.sites if site.key == "valor")
    scraper = SiteScraper(configuration, site)

    html = """
    <html><head><title>Marco do saneamento</title></head>
    <body><article><p>O setor de saneamento básico avança com novas regras
    para concessões e tarifas em todo o país, sem citar empresas específicas
  no momento da publicação desta matéria especial sobre infraestrutura.</p></article></body></html>
    """

    with patch("modules.scrapers.sites.base.fetch_text", return_value=html):
        record = scraper._fetch_article(
            SearchHit(
                url="https://valor.globo.com/empresas/noticia/2024/03/01/marco.ghtml",
                published="2024-03-01",
            ),
            since_date=__import__("datetime").date(2024, 1, 1),
            until_date=__import__("datetime").date(2024, 12, 31),
            timeout=5,
            delay=0,
            min_chars=40,
            seen_urls=set(),
            state=None,
            collection_mode="broad",
        )

    assert record is not None
    assert record["empresa"] == PENDING_COMPANY
    assert record["ticker"] == ""
    assert record["setor"] == "Saneamento"


def test_corpus_split_classified_and_pending(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_csv = raw_dir / "test.csv"
    raw_csv.write_text(
        "id,data,empresa,setor,ticker,titulo,noticia,fonte,url\n"
        "a,2024-01-01,Sabesp,Saneamento,SBSP3,T,Sabesp anuncia,IM,https://ex/a\n"
        f"b,2024-01-02,{PENDING_COMPANY},Saneamento,,T,saneamento setor,IM,https://ex/b\n"
        "c,2024-01-03,Saneamento,Saneamento,SETOR,T,gen,IM,https://ex/c\n",
        encoding="utf-8",
    )
    corpus_path = tmp_path / "noticias.csv"
    pending_path = tmp_path / "pendentes.csv"

    result = build_merged_corpus(
        raw_dir=raw_dir,
        corpus_path=corpus_path,
        pending_path=pending_path,
    )

    assert result.classified_count == 1
    assert result.pending_count == 1
    assert result.discarded_count == 1
    assert "Sabesp" in corpus_path.read_text(encoding="utf-8")
    assert PENDING_COMPANY in pending_path.read_text(encoding="utf-8")
