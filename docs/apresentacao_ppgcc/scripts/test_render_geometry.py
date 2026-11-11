#!/usr/bin/env python3
"""Testes sintéticos de geometria do render Beamer (gráficos e escopo)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_beamer as rb  # noqa: E402


def test_chart_scope_origin_bottom_left() -> None:
    scope = rb._chart_scope([10.0, 30.0, 80.0, 40.0])
    assert "-0.70000\\paperheight" in scope, "origem vertical deve ser y+h (70%)"
    assert "0.80000\\paperwidth" in scope


def test_vertical_bar_inside_clip() -> None:
    el = {
        "rect": [10, 35, 80, 40],
        "data": [
            {"dia": "Seg", "noticias": 3},
            {"dia": "Ter", "noticias": 5},
        ],
        "y_domain": [0, 6],
        "y_key": "noticias",
        "x_key": "dia",
    }
    tex = rb.render_chart_bar_vertical(el)
    for m in re.finditer(r"rectangle \(([0-9.]+),([0-9.]+)\) rectangle \(([0-9.]+),([0-9.]+)\)", tex):
        _, y0, _, y1 = map(float, m.groups())
        assert 0 <= min(y0, y1) and max(y0, y1) <= 1.05, "barra fora do clip nominal"
    assert "\\clip (0,0) rectangle (1,1)" in tex


def test_horizontal_bar_inside_clip() -> None:
    el = {
        "rect": [15, 30, 70, 35],
        "data": [{"fonte": "A", "noticias": 100}, {"fonte": "B", "noticias": 50}],
        "x_key": "noticias",
        "y_key": "fonte",
    }
    tex = rb.render_chart_bar_horizontal(el)
    assert "\\clip (0,0) rectangle (1,1)" in tex
    fills = re.findall(
        r"\\fill\[color=\{[^}]+\}\] \(([0-9.]+),([0-9.]+)\) rectangle \(([0-9.]+),([0-9.]+)\)",
        tex,
    )
    for x0, y0, x1, y1 in fills:
        for v in (float(y0), float(y1)):
            assert 0 <= v <= 1.05, f"barra horizontal y={v} fora do intervalo"


def test_interval_horizontal_geometry() -> None:
    el = {
        "rect": [10, 40, 80, 30],
        "data": [{"estimativa": 0.04, "inferior": -0.127, "superior": 0.241}],
        "x_domain": [-0.2, 0.3],
        "zero_line": True,
        "value_labels": True,
    }
    tex = rb.render_chart_interval_horizontal(el)
    assert "0.580" in tex  # yc
    assert "\\clip (0,0) rectangle (1,1)" in tex


def run_all() -> int:
    tests = [
        test_chart_scope_origin_bottom_left,
        test_vertical_bar_inside_clip,
        test_horizontal_bar_inside_clip,
        test_interval_horizontal_geometry,
    ]
    failed: list[str] = []
    for fn in tests:
        try:
            fn()
        except AssertionError as exc:
            failed.append(f"{fn.__name__}: {exc}")
    if failed:
        for f in failed:
            print(f"FALHA: {f}", file=sys.stderr)
        return 1
    print(f"OK: {len(tests)} testes de geometria")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_all())
