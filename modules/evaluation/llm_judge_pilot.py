"""Pilot batch for LLM-as-judge (qualification)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modules.evaluation.core.settings import load_evaluation_settings
from modules.evaluation.judges.hf_causal_judge import HfCausalLabelJudge
OUTPUT_COLUMNS = [
    "news_id",
    "impacto_alvo",
    "rotulo_llm_juiz",
    "notas_llm",
    "modelo",
    "prompt_versao",
]


def _load_corpus(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "news_id" not in frame.columns and "id" in frame.columns:
        frame["news_id"] = frame["id"]
    title_col = "titulo" if "titulo" in frame.columns else "title"
    body_col = "noticia" if "noticia" in frame.columns else "text"
    if body_col not in frame.columns:
        body_col = "content" if "content" in frame.columns else title_col
    return frame[["news_id", title_col, body_col]].rename(
        columns={title_col: "titulo", body_col: "noticia"}
    )


def _select_news_ids(
    manual_labels: Path | None,
    corpus: pd.DataFrame,
    *,
    limit: int,
) -> list[str]:
    if manual_labels and manual_labels.is_file():
        labels = pd.read_csv(manual_labels)
        if "ambiguo" in labels.columns:
            amb = labels[labels["ambiguo"].astype(str).str.lower().isin({"true", "1", "yes"})]
            if not amb.empty:
                return list(amb["news_id"].head(limit))
        if "tipologia" in labels.columns:
            roundups = labels[labels["tipologia"] == "roundup_agenda"]
            if not roundups.empty:
                return list(roundups["news_id"].head(limit))
    return list(corpus["news_id"].head(limit))


def run_pilot(
    *,
    limit: int = 10,
    model_id: str,
    mock: bool = False,
    output_csv: Path | None = None,
) -> Path:
    settings = load_evaluation_settings()
    corpus_path = settings.strict_corpus_path
    out_path = output_csv or settings.llm_judge_output_csv
    out_path.parent.mkdir(parents=True, exist_ok=True)

    corpus = _load_corpus(corpus_path)
    manual_path = settings.manual_labels_path
    manual_file = manual_path if manual_path.is_file() else None
    candidates = _select_news_ids(manual_file, corpus, limit=limit)

    existing: set[str] = set()
    if out_path.is_file():
        prev = pd.read_csv(out_path)
        if "news_id" in prev.columns:
            existing = set(prev["news_id"].astype(str))

    todo = [nid for nid in candidates if str(nid) not in existing][:limit]
    if not todo:
        return out_path

    subset = corpus[corpus["news_id"].isin(todo)]
    judge = HfCausalLabelJudge(
        model_id=model_id,
        prompt_version=settings.llm_judge_prompt_version,
        mock=mock,
    )
    items = [
        (str(row.news_id), str(row.titulo), str(row.noticia))
        for row in subset.itertuples(index=False)
    ]
    predictions = judge.judge(items)

    rows = []
    for pred in predictions:
        rows.append(
            {
                "news_id": pred.news_id,
                "impacto_alvo": "",
                "rotulo_llm_juiz": pred.label,
                "notas_llm": pred.rationale,
                "modelo": pred.judge_id,
                "prompt_versao": pred.prompt_version,
            }
        )
    new_frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if out_path.is_file():
        combined = pd.concat([pd.read_csv(out_path), new_frame], ignore_index=True)
        combined = combined.drop_duplicates(subset=["news_id"], keep="last")
    else:
        combined = new_frame
    combined.to_csv(out_path, index=False)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Piloto LLM-judge (qualificação).")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--model-id",
        default="mistralai/Mistral-7B-Instruct-v0.3",
        help="Modelo Hugging Face (causal LM).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Sem carregar modelo (demonstração / CI).",
    )
    parser.add_argument("--output-csv", type=Path, default=None)
    args = parser.parse_args(argv)

    out = run_pilot(
        limit=args.limit,
        model_id=args.model_id,
        mock=args.mock,
        output_csv=args.output_csv,
    )
    print(f"Piloto gravado em: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
