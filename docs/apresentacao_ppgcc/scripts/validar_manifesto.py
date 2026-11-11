#!/usr/bin/env python3
"""Valida manifesto (29+8), fatos científicos e assets antes do build PDF."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dados" / "manifesto_slides.json"
FATOS = ROOT / "dados" / "fatos_cientificos.json"
ASSETS = ROOT / "assets"


def main() -> int:
    errors: list[str] = []
    if not MANIFEST.is_file():
        errors.append(f"Manifesto ausente: {MANIFEST}")
    if not FATOS.is_file():
        errors.append(f"Fatos ausentes: {FATOS}")
    if errors:
        for e in errors:
            print(f"ERRO: {e}", file=sys.stderr)
        return 1

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    slides = data.get("slides", [])
    backup = data.get("backup", [])

    if len(slides) != data.get("slides_main_count", 29):
        errors.append("Contagem de slides principais não bate com slides_main_count")
    if len(backup) != data.get("slides_backup_count", 8):
        errors.append("Contagem de apoio não bate com slides_backup_count")
    if sum(s.get("seconds", 0) for s in slides) != data.get("time_target_seconds", 1800):
        errors.append("Soma de seconds dos principais != time_target_seconds")

    for s in slides:
        for key in (
            "id",
            "title",
            "source",
            "screen",
            "voice",
            "visual",
            "objective",
            "on_screen",
            "transition",
        ):
            if not s.get(key):
                errors.append(f"Campo ausente {key} em {s.get('id')}")
        if s.get("on_screen") and not isinstance(s.get("on_screen"), list):
            errors.append(f"on_screen deve ser lista em {s.get('id')}")
        if len(s.get("screen", [])) > 6:
            errors.append(f"Muitos bullets em {s['id']}")

    for s in backup:
        for key in ("id", "title", "screen", "voice", "visual", "objective", "on_screen", "transition"):
            if not s.get(key):
                errors.append(f"Campo ausente {key} em backup {s.get('id')}")

    figures = {
        "figura_2_soft_iti_noticias.png",
        "figura_3_meias_vidas.png",
        "figura_4_contrastes_bootstrap.png",
    }
    for name in figures:
        if not (ASSETS / name).is_file():
            errors.append(f"Asset ausente: assets/{name}")

    fatos = json.loads(FATOS.read_text(encoding="utf-8"))
    if not fatos.get("ancoras"):
        errors.append("fatos_cientificos.json sem ancoras")

    if errors:
        for e in errors:
            print(f"ERRO: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(slides)} principais + {len(backup)} apoio; "
        f"alvo {data.get('time_target_seconds')}s; assets e âncoras presentes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
