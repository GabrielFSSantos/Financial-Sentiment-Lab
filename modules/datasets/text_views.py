"""Preparação de entradas textuais (documento vs. contexto focal) — sem inferência."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Sequence

import yaml
from pathlib import Path

DEFAULT_ENTITIES_PATH = Path(__file__).resolve().parents[2] / "configs" / "entities.yaml"


@dataclass(frozen=True)
class TextViewResult:
    text: str
    view_id: str
    view_hash: str
    target_visible: bool
    status: str  # ok | not_evaluable
    spans: tuple[tuple[int, int], ...]
    coreference_unresolved: bool
    token_count_original: int | None = None


def _load_aliases(entity_key: str, entities_path: Path = DEFAULT_ENTITIES_PATH) -> list[str]:
    data = yaml.safe_load(entities_path.read_text(encoding="utf-8"))
    key = entity_key.lower()
    names: list[str] = []
    for ent in data.get("entities", []):
        company = str(ent.get("company", ""))
        if key in company.lower() or company.lower().startswith(key):
            names.extend([company, str(ent.get("ticker", ""))])
    for alias in data.get("name_aliases", []):
        if str(alias.get("company", "")).lower() == key:
            names.append(str(alias.get("match", "")))
    if not names:
        names = [entity_key]
    return [n for n in names if n]


def _word_boundary_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def build_document_view(title: str, body: str) -> TextViewResult:
    combined = f"{title.strip()}\n{body.strip()}".strip()
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
    return TextViewResult(
        text=combined,
        view_id="document_v1",
        view_hash=digest,
        target_visible=True,
        status="ok" if combined else "not_evaluable",
        spans=((0, len(combined)),) if combined else (),
        coreference_unresolved=False,
        token_count_original=len(combined.split()),
    )


def build_entity_context_view(
    title: str,
    body: str,
    entity_key: str,
    *,
    neighbors: int = 1,
    entities_path: Path = DEFAULT_ENTITIES_PATH,
) -> TextViewResult:
    """Seleciona sentenças com menção explícita ao alvo (+ vizinhas)."""

    aliases = _load_aliases(entity_key, entities_path)
    sentences = _split_sentences(body)
    if title.strip():
        sentences = [title.strip()] + sentences

    patterns = [_word_boundary_pattern(a) for a in aliases]
    selected: set[int] = set()
    for index, sentence in enumerate(sentences):
        if any(p.search(sentence) for p in patterns):
            for offset in range(-neighbors, neighbors + 1):
                j = index + offset
                if 0 <= j < len(sentences):
                    selected.add(j)

    if not selected:
        return TextViewResult(
            text="",
            view_id="entity_context_v1",
            view_hash="",
            target_visible=False,
            status="not_evaluable",
            spans=(),
            coreference_unresolved=True,
        )

    ordered = [sentences[i] for i in sorted(selected)]
    combined = "\n".join(ordered)
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
    return TextViewResult(
        text=combined,
        view_id="entity_context_v1",
        view_hash=digest,
        target_visible=True,
        status="ok",
        spans=tuple(),
        coreference_unresolved=True,
    )
