#!/usr/bin/env python3
"""Gera docs/references/downloads_pending.md a partir de bibliography_manifest.csv."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/references/bibliography_manifest.csv"
OUT = ROOT / "docs/references/downloads_pending.md"


def main() -> int:
    if not MANIFEST.is_file():
        print(f"Manifest ausente: {MANIFEST}", file=sys.stderr)
        return 1
    lines = [
        "# PDFs e referências pendentes",
        "",
        "Gerado a partir de `bibliography_manifest.csv`. Gabriel: baixar manualmente quando aplicável.",
        "",
        "| Chave | Título | Status | URL | Notas |",
        "|---|---|---|---|---|",
    ]
    import csv

    with MANIFEST.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            status = (row.get("status") or "pending").strip()
            if status == "ok":
                continue
            lines.append(
                f"| `{row.get('cite_key','')}` | {row.get('title','')} | {status} | "
                f"{row.get('primary_url','')} | {row.get('notes','')} |"
            )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
