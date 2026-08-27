"""Inicializa manifest.json da campanha Sabesp."""

from __future__ import annotations

import json
from pathlib import Path

from modules.experiment import PROJECT_ROOT
from modules.experiment.campaign.generate_configs import RUN_SPECS
from modules.experiment.campaign.manifest import CampaignRunRecord, save_manifest

MANIFEST_PATH = PROJECT_ROOT / "outputs" / "campaigns" / "sabesp_2026" / "manifest.json"


def main() -> int:
    runs: list[dict] = []
    for spec in RUN_SPECS:
        record = CampaignRunRecord(
            run_id=spec["run_id"],
            hypothesis=spec["hypothesis"],
            config_path=f"configs/experiments/sabesp/{spec['file']}",
            model=spec["model"],
            dataset="saneamento_sabesp_strict_event",
            alpha=spec["alpha"],
            equation=spec["equation"],
            frequency="weekly",
            status="pending",
        )
        runs.append(
            {
                **record.__dict__,
                "research_iti_column": spec.get("research_iti_column", "iti_liquido_last"),
            }
        )

    payload = {
        "campaign": "sabesp_2026",
        "description": "Campanha strict ITI semanal Sabesp (nov/23–abr/24)",
        "baseline_run_id": "sabesp_r0_baseline",
        "runs": runs,
    }
    save_manifest(MANIFEST_PATH, payload)
    print(f"Manifest: {MANIFEST_PATH} ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
