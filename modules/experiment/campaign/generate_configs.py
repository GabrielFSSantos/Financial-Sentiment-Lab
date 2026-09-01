"""Gera configs YAML da campanha Sabesp a partir do experiment base."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from modules.experiment import PROJECT_ROOT

BASE_CONFIG_PATH = PROJECT_ROOT / "configs" / "experiment.yaml"
OUTPUT_DIR = PROJECT_ROOT / "configs" / "campaigns" / "sabesp_2026" / "experiments"

RUN_SPECS: list[dict] = [
    {
        "file": "r0_baseline.yaml",
        "run_id": "sabesp_r0_baseline",
        "hypothesis": "Referência corrigida: strict, Sabesp, ITI semanal",
        "model": "finbert_ptbr",
        "alpha": 0.85,
        "equation": "full",
        "overrides": {},
    },
    {
        "file": "r1_alpha070.yaml",
        "run_id": "sabesp_r1_alpha070",
        "hypothesis": "EWMA mais reativo (alpha 0.70) ajuda vs B0?",
        "model": "finbert_ptbr",
        "alpha": 0.70,
        "equation": "full",
        "overrides": {"temporal_index": {"alpha": 0.70}},
    },
    {
        "file": "r2_alpha095.yaml",
        "run_id": "sabesp_r2_alpha095",
        "hypothesis": "Mais memória (alpha 0.95) suaviza ruído?",
        "model": "finbert_ptbr",
        "alpha": 0.95,
        "equation": "full",
        "overrides": {"temporal_index": {"alpha": 0.95}},
    },
    {
        "file": "r3_no_novelty.yaml",
        "run_id": "sabesp_r3_no_novelty",
        "hypothesis": "Novelty u agrega informação?",
        "model": "finbert_ptbr",
        "alpha": 0.85,
        "equation": "full sem u",
        "overrides": {"temporal_index": {"disabled_dimensions": ["novelty"]}},
    },
    {
        "file": "r4_no_event.yaml",
        "run_id": "sabesp_r4_no_event",
        "hypothesis": "Peso de evento e heurísticas ajudam?",
        "model": "finbert_ptbr",
        "alpha": 0.85,
        "equation": "full sem e",
        "overrides": {
            "temporal_index": {
                "disabled_dimensions": ["event_weight"],
                "dimensions": {"heuristics": {"enabled": False}},
            }
        },
    },
    {
        "file": "r5_no_relevance.yaml",
        "run_id": "sabesp_r5_no_relevance",
        "hypothesis": "Relevance r estabiliza pesos?",
        "model": "finbert_ptbr",
        "alpha": 0.85,
        "equation": "full sem r",
        "overrides": {"temporal_index": {"disabled_dimensions": ["relevance"]}},
    },
    {
        "file": "r6_simplified.yaml",
        "run_id": "sabesp_r6_simplified",
        "hypothesis": "Dimensões extras são ruído?",
        "model": "finbert_ptbr",
        "alpha": 0.85,
        "equation": "simplified_dc",
        "overrides": {"temporal_index": {"equation_mode": "simplified_dc"}},
    },
    {
        "file": "r7_horizon_fixed.yaml",
        "run_id": "sabesp_r7_horizon_fixed",
        "hypothesis": "Modulação de alpha por h confunde?",
        "model": "finbert_ptbr",
        "alpha": 0.85,
        "equation": "full",
        "overrides": {"temporal_index": {"horizon": {"mode": "fixed"}}},
    },
    {
        "file": "r8_weekly_mean.yaml",
        "run_id": "sabesp_r8_weekly_mean",
        "hypothesis": "Média semanal vs último dia da semana?",
        "model": "finbert_ptbr",
        "alpha": 0.85,
        "equation": "full",
        "overrides": {},
        "research_iti_column": "iti_liquido_mean",
    },
    {
        "file": "r9_ensemble.yaml",
        "run_id": "sabesp_r9_ensemble",
        "hypothesis": "Ensemble PT-BR muda o sinal?",
        "model": "pt_br_financial_sentiment_analysis",
        "alpha": 0.85,
        "equation": "full",
        "overrides": {},
    },
]


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def generate_configs() -> list[Path]:
    base = yaml.safe_load(BASE_CONFIG_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for spec in RUN_SPECS:
        config = _deep_merge(base, spec.get("overrides", {}))
        config = _deep_merge(
            config,
            {
                "execution": {"overwrite_existing_run": True},
            },
        )
        path = OUTPUT_DIR / spec["file"]
        path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
        paths.append(path)
    return paths


if __name__ == "__main__":
    written = generate_configs()
    print(f"Gerados {len(written)} configs em {OUTPUT_DIR}")
