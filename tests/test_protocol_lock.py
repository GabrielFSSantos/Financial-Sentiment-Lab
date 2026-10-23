"""Protocol lock P11."""

from pathlib import Path

from modules.experiment.campaign.protocol_lock import build_protocol_lock, write_protocol_lock


def test_build_protocol_lock(project_root: Path, tmp_path: Path) -> None:
    corpus = project_root / "outputs/corpus_inventory/iti_v2_p02"
    if not (corpus / "corpus_manifest.json").is_file():
        return
    payload = build_protocol_lock(
        corpus_dir=corpus,
        protocol_path=project_root / "configs/campaigns/iti_v2/protocol.yaml",
        analysis_plan_path=project_root / "configs/campaigns/iti_v2/analysis_plan.yaml",
        project_root=project_root,
    )
    assert payload["hashes"]["protocol_sha256"]
    out = write_protocol_lock(tmp_path / "protocol_lock.json", payload)
    assert out.is_file()
