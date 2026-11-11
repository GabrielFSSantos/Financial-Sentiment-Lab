#!/usr/bin/env python3
"""Exporta roteiro de fala único (Markdown) a partir do manifesto."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dados" / "manifesto_slides.json"
BUILD = ROOT / "build" / "apresentacao_ppgcc_roteiro.md"
OUTPUT = ROOT / "output" / "apresentacao_ppgcc_roteiro.md"


def _fmt_duration(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _slide_section(s: dict, *, backup: bool = False) -> list[str]:
    lines: list[str] = []
    if backup:
        lines.append(f"## {s.get('id')} — {s.get('title', '')}")
    else:
        n = int(s.get("n", 0))
        lines.append(f"## {n:02d} — {s.get('title', '')}")
    lines.append("")
    if not backup:
        seconds = int(s.get("seconds", 0))
        words = s.get("words")
        source = s.get("source", "")
        words_part = f" · {words} palavras" if words is not None else ""
        lines.append(
            f"*Alvo: {_fmt_duration(seconds)} ({seconds} s){words_part} · Fonte: {source}*"
        )
        lines.append("")
    obj = (s.get("objective") or "").strip()
    if obj:
        lines.append(f"**Objetivo:** {obj}")
        lines.append("")
    voice = (s.get("voice") or "").strip()
    lines.append("**Fala:**")
    lines.append("")
    lines.append(voice)
    lines.append("")
    on_screen = s.get("on_screen") or []
    if on_screen:
        lines.append("**Na tela:**")
        for item in on_screen:
            lines.append(f"- {item}")
        lines.append("")
    trans = (s.get("transition") or "").strip()
    if trans:
        lines.append(f"**Transição:** {trans}")
        lines.append("")
    return lines


def main() -> int:
    if not MANIFEST.is_file():
        print(f"ERRO: manifesto ausente: {MANIFEST}", file=sys.stderr)
        return 1

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    slides = data.get("slides", [])
    backup = data.get("backup", [])
    errors: list[str] = []

    for s in slides + backup:
        sid = s.get("id", "?")
        if not (s.get("voice") or "").strip():
            errors.append(f"voice ausente ou vazio em {sid}")
        if not (s.get("objective") or "").strip():
            errors.append(f"objective ausente em {sid}")

    if errors:
        for e in errors:
            print(f"ERRO: {e}", file=sys.stderr)
        return 1

    total_seconds = sum(s.get("seconds", 0) for s in slides)
    total_words = sum(s.get("words", 0) for s in slides if isinstance(s.get("words"), int))
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %z")

    out_lines: list[str] = [
        f"# {data.get('title', 'Apresentação PPGCC')}",
        "",
        f"Roteiro gerado por `make pdf` em {now}. **Não editar à mão** — altere `dados/manifesto_slides.json`.",
        "",
        f"- Slides principais: {len(slides)}",
        f"- Tempo-alvo somado: {_fmt_duration(total_seconds)} ({total_seconds} s)",
        f"- Palavras (campo `words` nos principais): {total_words}",
        "",
        "## Slides principais (defesa ~30 min)",
        "",
    ]

    for s in slides:
        out_lines.extend(_slide_section(s))

    out_lines.extend(
        [
            "## Slides de apoio (fora dos 30 min)",
            "",
            "Material de reserva para perguntas; não compõe o tempo-alvo da qualificação.",
            "",
        ]
    )

    for s in backup:
        out_lines.extend(_slide_section(s, backup=True))

    out_lines.append(f"---\n\n*Total de slides: {len(slides)} + {len(backup)} apoio.*")

    BUILD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(out_lines)
    BUILD.write_text(text, encoding="utf-8")
    shutil.copy2(BUILD, OUTPUT)
    print(f"OK: roteiro → {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
