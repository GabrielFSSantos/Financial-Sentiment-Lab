#!/usr/bin/env python3
"""Testes de altura de conteúdo no manifesto."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from layout_content_metrics import validate_element_height  # noqa: E402

MANIFEST = ROOT / "dados" / "manifesto_slides.json"


def test_no_one_percent_text_boxes() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad: list[str] = []
    for section in ("slides", "backup"):
        for slide in data.get(section, []):
            sid = slide.get("id", "?")
            for el in slide.get("elements") or []:
                r = el.get("rect")
                if not r or el.get("type") not in ("text", "formula"):
                    continue
                if r[3] < 2.0 and (el.get("text") or el.get("latex")):
                    bad.append(f"{sid}/{el.get('id')} h={r[3]}")
    assert not bad, bad


def main() -> int:
    tests = [test_no_one_percent_text_boxes]
    for fn in tests:
        try:
            fn()
        except AssertionError as exc:
            print(f"FALHA: {fn.__name__}: {exc}", file=sys.stderr)
            return 1
    print(f"OK: {len(tests)} testes de layout de conteúdo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
