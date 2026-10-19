"""Pilot batch for LLM-as-judge (manual annotation eval)."""

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


def _load_news_ids_file(path: Path) -> list[str]:
    frame = pd.read_csv(path)
    id_col = "news_id" if "news_id" in frame.columns else frame.columns[0]
    return [str(x).strip() for x in frame[id_col].tolist() if str(x).strip()]


def _all_manual_news_ids(manual_labels: Path) -> list[str]:
    labels = pd.read_csv(manual_labels)
    if "news_id" not in labels.columns:
        raise ValueError("manual_labels sem coluna news_id")
    return [str(x).strip() for x in labels["news_id"].tolist() if str(x).strip()]


def _select_news_ids(
    manual_labels: Path | None,
    corpus: pd.DataFrame,
    *,
    limit: int,
    explicit_ids: list[str] | None = None,
    all_manual: bool = False,
) -> list[str]:
    if all_manual and manual_labels and manual_labels.is_file():
        return _all_manual_news_ids(manual_labels)[:limit]
    if explicit_ids:
        return explicit_ids[:limit]
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
    news_ids_file: Path | None = None,
    all_manual: bool = False,
) -> Path:
    settings = load_evaluation_settings()
    corpus_path = settings.strict_corpus_path
    out_path = output_csv or settings.llm_judge_output_csv
    out_path.parent.mkdir(parents=True, exist_ok=True)

    corpus = _load_corpus(corpus_path)
    manual_path = settings.manual_labels_path
    manual_file = manual_path if manual_path.is_file() else None
    explicit = (
        _load_news_ids_file(news_ids_file)
        if news_ids_file and news_ids_file.is_file()
        else None
    )
    candidates = _select_news_ids(
        manual_file,
        corpus,
        limit=limit,
        explicit_ids=explicit,
        all_manual=all_manual,
    )

    existing: set[str] = set()
    if out_path.is_file():
        prev = pd.read_csv(out_path)
        if "news_id" in prev.columns:
            existing = set(prev["news_id"].astype(str))

    todo = [nid for nid in candidates if str(nid) not in existing][:limit]
    if not todo:
        return out_path

    judge = HfCausalLabelJudge(
        model_id=model_id,
        prompt_version=settings.llm_judge_prompt_version,
        mock=mock,
    )

    def _append_row(pred) -> None:
        row = {
            "news_id": pred.news_id,
            "impacto_alvo": "",
            "rotulo_llm_juiz": pred.label,
            "notas_llm": pred.rationale,
            "modelo": pred.judge_id,
            "prompt_versao": pred.prompt_version,
        }
        new_frame = pd.DataFrame([row], columns=OUTPUT_COLUMNS)
        if out_path.is_file():
            combined = pd.concat([pd.read_csv(out_path), new_frame], ignore_index=True)
            combined = combined.drop_duplicates(subset=["news_id"], keep="last")
        else:
            combined = new_frame
        combined.to_csv(out_path, index=False)

    total = len(todo)
    for index, nid in enumerate(todo, start=1):
        row = corpus[corpus["news_id"].astype(str) == str(nid)]
        if row.empty:
            print(f"[{index}/{total}] SKIP {nid} (ausente no corpus)", flush=True)
            continue
        rec = row.iloc[0]
        pred = judge.judge(
            [(str(nid), str(rec["titulo"]), str(rec["noticia"]))]
        )[0]
        _append_row(pred)
        print(
            f"[{index}/{total}] {nid} -> {pred.label}",
            flush=True,
        )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Piloto LLM-judge (avaliação manual).")
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
    parser.add_argument(
        "--news-ids-file",
        type=Path,
        default=None,
        help="CSV com coluna news_id para piloto (prioridade sobre heurística).",
    )
    parser.add_argument(
        "--all-manual",
        action="store_true",
        help="Rotular todos os news_id de manual_labels_100.csv (até --limit).",
    )
    args = parser.parse_args(argv)

    out = run_pilot(
        limit=args.limit,
        model_id=args.model_id,
        mock=args.mock,
        output_csv=args.output_csv,
        news_ids_file=args.news_ids_file,
        all_manual=args.all_manual,
    )
    print(f"Piloto gravado em: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
