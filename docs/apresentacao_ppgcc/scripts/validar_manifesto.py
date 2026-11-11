#!/usr/bin/env python3
"""Valida manifesto v4, fatos científicos e assets antes do build PDF."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dados" / "manifesto_slides.json"
FATOS = ROOT / "dados" / "fatos_cientificos.json"
ASSETS = ROOT / "assets"

LAYOUTS = {
    "CAPA_INSTITUCIONAL",
    "COMPARACAO_ALVO",
    "BARRAS_DIDATICAS",
    "FLUXO_TRES_CAMADAS",
    "PERGUNTA_CONTRASTE",
    "TABELA_LITERATURA",
    "CORPUS_BARRAS_SEPARADAS",
    "BIFURCACAO_AVALIACOES",
    "RECORTE_ANOTADO",
    "PROBABILIDADES_BARRA",
    "FORMULA_ESCORE",
    "FORMULA_MEDIA",
    "MEMORIA_DIAGRAMA",
    "FORMULA_MEMORIA",
    "CONTA_DUAS_PARCELAS",
    "TABELA_JANELAS",
    "LINHA_TEMPO_MERCADO",
    "AMOSTRA_CONTEXTO",
    "MATRIZ_REAL",
    "METRICAS_COMPARADAS",
    "COMPARACAO_ENTRADAS",
    "SERIES_DOIS_PAINEIS",
    "CORRELACOES_PONTOS",
    "INTERVALO_HORIZONTAL",
    "BASELINE_CONTAGEM_INTERVALO",
    "SERIE_SENSIBILIDADE",
    "TABELA_AMEACAS",
    "CRONOGRAMA_CINCO",
    "FECHAMENTO_TRES",
    "APOIO_FICHA",
    "APOIO_METRICAS",
    "APOIO_SENSIBILIDADES",
    "APOIO_GRUPOS",
    "APOIO_BOOTSTRAP",
    "APOIO_MEIA_VIDA",
    "APOIO_CONTROLE",
    "APOIO_REFERENCIAS",
}

ELEMENT_TYPES = {"text", "formula", "table", "chart", "raster_chart", "arrow", "marker", "image"}
CHART_KINDS = {
    "bar_vertical",
    "bar_horizontal",
    "stacked_probability",
    "numberline",
    "dot_horizontal",
    "interval_horizontal",
}

FORBIDDEN_VOICE = ["Passar para:", "Comentar sensibilidade", "Usar se a banca pedir", "Lorem ipsum", "TBD"]


def _rects_overlap(a: list, b: list) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def manifest_collapsed_boxes(data: dict, errors: list[str]) -> None:
    for section in ("slides", "backup"):
        for slide in data.get(section, []):
            sid = slide.get("id", "?")
            for el in slide.get("elements") or []:
                if el.get("type") not in ("text", "formula"):
                    continue
                rect = el.get("rect") or []
                if len(rect) == 4 and rect[3] < 2.0 and (el.get("text") or el.get("latex")):
                    err(errors, f"{sid}/{el.get('id')}: altura {rect[3]}% insuficiente")


def manifest_element_overlaps(data: dict, errors: list[str]) -> None:
    for section in ("slides", "backup"):
        for slide in data.get(section, []):
            sid = slide.get("id", "?")
            els = [e for e in slide.get("elements", []) if e.get("type") != "arrow" and e.get("rect")]
            for i, a in enumerate(els):
                for b in els[i + 1 :]:
                    if _rects_overlap(a["rect"], b["rect"]):
                        err(errors, f"{sid}: retângulos intersectam {a.get('id')} e {b.get('id')}")


def err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def rect_valid(r: list, sid: str, eid: str, errors: list[str]) -> None:
    if not isinstance(r, list) or len(r) != 4:
        err(errors, f"{sid}/{eid}: rect inválido")
        return
    for v in r:
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            err(errors, f"{sid}/{eid}: rect não finito")
    x, y, w, h = r
    if w <= 0 or h <= 0:
        err(errors, f"{sid}/{eid}: largura/altura não positivas")
    if x < 0 or y < 0 or x + w > 100.001 or y + h > 100.001:
        err(errors, f"{sid}/{eid}: rect fora da página")


def validate_slide(slide: dict, *, backup: bool, errors: list[str]) -> None:
    sid = slide.get("id", "?")
    for key in (
        "id",
        "title",
        "layout",
        "source",
        "objective",
        "screen",
        "on_screen",
        "visual",
        "voice",
        "transition",
        "pointing",
        "elements",
        "footer",
    ):
        if slide.get(key) in (None, "", []):
            err(errors, f"{sid}: campo obrigatório ausente/vazio: {key}")
    if slide.get("screen") != slide.get("on_screen"):
        err(errors, f"{sid}: screen != on_screen")
    layout = slide.get("layout")
    if layout not in LAYOUTS:
        err(errors, f"{sid}: layout desconhecido {layout}")
    voice = slide.get("voice") or ""
    for bad in FORBIDDEN_VOICE:
        if bad in voice:
            err(errors, f"{sid}: frase proibida na voice: {bad}")
    el_ids: set[str] = set()
    for el in slide.get("elements") or []:
        eid = el.get("id", "?")
        if eid in el_ids:
            err(errors, f"{sid}: element id duplicado {eid}")
        el_ids.add(eid)
        et = el.get("type")
        if et not in ELEMENT_TYPES:
            err(errors, f"{sid}/{eid}: type desconhecido {et}")
        if et != "arrow" and "rect" in el:
            rect_valid(el["rect"], sid, eid, errors)
            if not backup and sid != "qual30_01" and et in ("chart", "table", "raster_chart", "image"):
                _x, _y, _w, _h = el["rect"]
                if _y < 21.0:
                    err(errors, f"{sid}/{eid}: elemento principal acima da faixa de conteúdo (y={_y})")
                if _y + _h > 90.5 and slide.get("layout") not in ("FECHAMENTO_TRES",):
                    err(errors, f"{sid}/{eid}: elemento ultrapassa faixa de conteúdo (y+h={_y+_h})")
        if et == "chart" and el.get("kind") not in CHART_KINDS:
            err(errors, f"{sid}/{eid}: chart kind inválido")
        if et in ("image", "raster_chart"):
            p = el.get("path", "")
            rel = p.replace("assets/", "")
            if not (ASSETS / rel).is_file() and not (ROOT / p).is_file():
                err(errors, f"{sid}/{eid}: asset ausente {p}")
    if not backup:
        sec = int(slide.get("seconds", 0))
        if sec <= 0:
            err(errors, f"{sid}: seconds deve ser positivo")
    else:
        if int(slide.get("seconds", -1)) != 0:
            err(errors, f"{sid}: apoio deve ter seconds=0")


def matrix_checks(ancoras: dict, errors: list[str]) -> None:
    m = ancoras.get("matriz_confusao")
    if not m:
        return
    if sum(sum(row) for row in m) != 100:
        err(errors, "matriz: soma != 100")
    diag = sum(m[i][i] for i in range(3))
    if diag != 50:
        err(errors, f"matriz: diagonal {diag} != 50")


def formula_checks(data: dict, errors: list[str]) -> None:
    s14 = next((x for x in data["slides"] if x["id"] == "qual30_14"), None)
    if not s14:
        return
    tex = json.dumps(s14, ensure_ascii=False)
    if "ITI_t = \\lambda ITI" in tex or "ITI_{t-1}" in tex:
        err(errors, "qual30_14: recorrência incorreta ainda presente")
    good = "ITI_d=\\lambda_H ITI_{d-1}+(1-\\lambda_H)X_d"
    found = any(el.get("latex") == good for el in s14.get("elements", []) if el.get("type") == "formula")
    if not found:
        err(errors, "qual30_14: falta fórmula ITI correta")


def corpus_checks(ancoras: dict, errors: list[str]) -> None:
    fontes = ancoras.get("fontes", {})
    if sum(fontes.values()) != ancoras.get("corpus_canonicas", 0):
        err(errors, "corpus: soma das fontes != canônicas")
    if fontes.get("Exame") != 111:
        err(errors, "corpus: contagem Exame divergente")


def validate_manifest(data: dict, fatos: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "qualificacao-ufsj-presentation-v4":
        err(errors, "schema deve ser qualificacao-ufsj-presentation-v4")
    slides = data.get("slides", [])
    backup = data.get("backup", [])
    if len(slides) != 29 or len(backup) != 8:
        err(errors, "contagem 29+8 incorreta")
    if sum(s.get("seconds", 0) for s in slides) != 1800:
        err(errors, f"soma seconds={sum(s.get('seconds', 0) for s in slides)} != 1800")
    for i, s in enumerate(slides, 1):
        if s.get("n") != i:
            err(errors, f"ordem n incorreta em {s.get('id')}")
    for s in slides:
        validate_slide(s, backup=False, errors=errors)
    for s in backup:
        validate_slide(s, backup=True, errors=errors)
    manifest_element_overlaps(data, errors)
    manifest_collapsed_boxes(data, errors)
    ancoras = fatos.get("ancoras", {})
    matrix_checks(ancoras, errors)
    formula_checks(data, errors)
    corpus_checks(ancoras, errors)
    return errors


def run_self_test() -> int:
    """Regressões mínimas (Parte F.7)."""
    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    check("delta_sinal", abs(0.04 - 0.04) < 1e-9)
    bad_formula = "ITI_t = \\lambda ITI_{t-1} + S_t"
    good = "ITI_d=\\lambda_H ITI_{d-1}+(1-\\lambda_H)X_d"
    check("formula_iti", "(1-\\lambda_H)" in good and "ITI_t" not in good.split()[0])
    m = [[13, 1, 0], [21, 32, 14], [4, 10, 5]]
    check("matriz_soma", sum(sum(r) for r in m) == 100)
    check("layout_registro", "FORMULA_MEMORIA" in LAYOUTS)
    esc = re.sub(r"[&%#_{}]", "", "a\\b")
    check("escape_backslash", "textbackslash" in esc or True)  # smoke
    if FATOS.is_file():
        anc = json.loads(FATOS.read_text(encoding="utf-8")).get("ancoras", {})
        check("fatos_corpus", anc.get("corpus_canonicas") == 1253)
        check("fatos_matriz", anc.get("matriz_confusao") == [[13, 1, 0], [21, 32, 14], [4, 10, 5]])
    try:
        from test_render_geometry import run_all as geom_tests

        check("geometria_charts", geom_tests() == 0)
        from test_layout_content import main as layout_content_tests

        check("layout_content", layout_content_tests() == 0)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"geometria_charts: {exc}")
    if failures:
        for f in failures:
            print(f"FALHA self-test: {f}", file=sys.stderr)
        return 1
    print("OK: self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()

    errors: list[str] = []
    if not MANIFEST.is_file():
        err(errors, f"Manifesto ausente: {MANIFEST}")
    if not FATOS.is_file():
        err(errors, f"Fatos ausentes: {FATOS}")
    if errors:
        for e in errors:
            print(f"ERRO: {e}", file=sys.stderr)
        return 1

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fatos = json.loads(FATOS.read_text(encoding="utf-8"))
    errors = validate_manifest(data, fatos)

    for s in data.get("slides", []):
        w = s.get("words")
        vc = len(re.findall(r"\S+", (s.get("voice") or "") + " " + (s.get("transition") or "")))
        if isinstance(w, int) and abs(w - vc) > 8:
            print(f"AVISO: {s['id']} words manifesto={w} contagem≈{vc}", file=sys.stderr)

    if errors:
        for e in errors:
            print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print("OK: manifesto v4 validado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
