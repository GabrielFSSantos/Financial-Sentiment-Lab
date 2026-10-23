"""Aceite automático do plano ITI-v2."""

from pathlib import Path

from modules.experiment.campaign.iti_v2_acceptance import run_acceptance


def test_acceptance_p02_and_configs(project_root: Path) -> None:
    corpus = project_root / "outputs/corpus_inventory/iti_v2_p02"
    if not (corpus / "corpus_manifest.json").is_file():
        return
    ok, results = run_acceptance(corpus_dir=corpus, run_id=None)
    failed = [r for r in results if not r.ok]
    assert ok, f"falhas: {[f.name for f in failed]}"
