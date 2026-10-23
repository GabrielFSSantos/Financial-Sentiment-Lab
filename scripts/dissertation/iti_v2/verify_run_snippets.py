#!/usr/bin/env python3
"""Confere coerência entre métricas do run, macros LaTeX e snippets gerados."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ROOT / "docs/Dissertacao_PPGCC/generated"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_macro(tex: str, name: str) -> str | None:
    match = re.search(rf"\\newcommand{{\\{name}}}{{([^}}]+)}}", tex)
    return match.group(1) if match else None


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "iti_v2_prod_20261022"
    run_dir = ROOT / "outputs/campaigns/iti_v2" / run_id
    errors: list[str] = []

    primary = run_dir / "metrics_primary.json"
    delta = run_dir / "metrics_primary_delta.json"
    macros_path = GENERATED / "results_macros.tex"
    snippet_path = GENERATED / "iti_v2_results_snippet.tex"

    for path in (primary, delta, macros_path, snippet_path):
        if not path.is_file():
            errors.append(f"ausente: {path}")
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1

    metrics = _read_json(primary)
    delta_row = _read_json(delta)
    macros = macros_path.read_text(encoding="utf-8")
    snippet = snippet_path.read_text(encoding="utf-8")

    checks = [
        ("n_panel", str(metrics.get("n_panel")), _parse_macro(macros, "ITIvTwoNPanel")),
        ("delta", f"{float(delta_row.get('delta')):.3f}".replace(".", ","), _parse_macro(macros, "ITIvTwoDeltaPrimary")),
        ("p_delta", f"{float(delta_row.get('p_value')):.3f}".replace(".", ","), _parse_macro(macros, "ITIvTwoDeltaP")),
    ]
    for label, expected, found in checks:
        if found is None or expected != found:
            errors.append(f"macro {label}: esperado {expected}, encontrado {found}")

    if f"$n={delta_row.get('n')}$" not in snippet:
        errors.append("snippet sem n do contraste principal")
    if f"$n={metrics.get('n_panel')}$" not in snippet:
        errors.append("snippet sem n do painel")

    manifest = run_dir / "run_manifest.json"
    if manifest.is_file():
        man = _read_json(manifest)
        if not man.get("corpus_manifest_sha256"):
            errors.append("run_manifest sem corpus_manifest_sha256 (reindexar após patch)")

    if errors:
        for item in errors:
            print(f"FALHA: {item}", file=sys.stderr)
        return 1

    print(f"OK: {run_id} coerente com {macros_path.name} e {snippet_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
