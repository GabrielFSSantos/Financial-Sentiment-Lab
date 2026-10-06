"""Overlay ``configs/campaigns/datasets.yaml`` sem sobrescrever o core."""

from __future__ import annotations

from pathlib import Path

import yaml

from modules.datasets.config.loader import load_datasets_configuration


def test_campaign_overlay_adds_datasets_without_removing_core(
    project_root: Path,
) -> None:
    configuration = load_datasets_configuration(project_root=project_root)
    keys = {item.key for item in configuration.datasets}

    assert "noticias_exemplo_ptbr" in keys
    assert "water_utilities_corpus" in keys
    assert "saneamento_sabesp_strict_event" in keys


def test_campaign_overlay_does_not_replace_existing_core_key(
    project_root: Path,
    tmp_path: Path,
) -> None:
    base_path = tmp_path / "datasets.yaml"
    base_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.0",
                "defaults": {
                    "language": "pt",
                    "format": "csv",
                    "reader": {
                        "encoding": "utf-8",
                        "delimiter": ",",
                        "quotechar": '"',
                        "header": 0,
                        "low_memory": False,
                        "skip_blank_lines": True,
                        "on_bad_lines": "error",
                    },
                    "validation": {
                        "strip_text": True,
                        "drop_empty_texts": True,
                        "fail_on_duplicate_ids": True,
                        "preserve_extra_columns": True,
                    },
                },
                "datasets": {
                    "core_ds": {
                        "enabled": True,
                        "order": 1,
                        "dataset_name": "core_ds",
                        "display_name": "Core",
                        "path": "data/noticias_exemplo_ptbr/noticias.csv",
                        "format": "csv",
                        "limits": {"max_rows": 1},
                        "columns": {
                            "news_id": "id",
                            "text": "noticia",
                            "date": "data",
                            "company": "empresa",
                            "sector": "setor",
                        },
                        "required_fields": ["news_id", "text"],
                        "labels": {
                            "available": False,
                            "normalize_case": True,
                            "strip_whitespace": True,
                            "mapping": {},
                        },
                        "dates": {
                            "available": True,
                            "format": "%Y-%m-%d",
                            "dayfirst": False,
                            "fail_on_invalid": True,
                            "output_format": "%Y-%m-%d",
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    overlay_dir = tmp_path / "configs" / "campaigns"
    overlay_dir.mkdir(parents=True)
    (overlay_dir / "datasets.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.0",
                "datasets": {
                    "core_ds": {
                        "enabled": False,
                        "order": 99,
                        "dataset_name": "should_not_replace",
                        "display_name": "Overlay",
                        "path": "data/missing.csv",
                        "format": "csv",
                        "limits": {},
                        "columns": {"news_id": "id", "text": "t"},
                        "required_fields": ["news_id"],
                        "labels": {
                            "available": False,
                            "normalize_case": True,
                            "strip_whitespace": True,
                            "mapping": {},
                        },
                        "dates": {"available": False},
                        "validation": {
                            "strip_text": True,
                            "drop_empty_texts": True,
                            "fail_on_duplicate_ids": True,
                            "preserve_extra_columns": True,
                        },
                    },
                    "campaign_only": {
                        "enabled": True,
                        "order": 2,
                        "dataset_name": "campaign_only",
                        "display_name": "Campaign",
                        "path": "data/noticias_exemplo_ptbr/noticias.csv",
                        "format": "csv",
                        "limits": {"max_rows": 1},
                        "columns": {
                            "news_id": "id",
                            "text": "noticia",
                            "date": "data",
                            "company": "empresa",
                            "sector": "setor",
                        },
                        "required_fields": ["news_id", "text"],
                        "labels": {
                            "available": False,
                            "normalize_case": True,
                            "strip_whitespace": True,
                            "mapping": {},
                        },
                        "dates": {
                            "available": True,
                            "format": "%Y-%m-%d",
                            "dayfirst": False,
                            "fail_on_invalid": True,
                            "output_format": "%Y-%m-%d",
                        },
                        "validation": {
                            "strip_text": True,
                            "drop_empty_texts": True,
                            "fail_on_duplicate_ids": True,
                            "preserve_extra_columns": True,
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    configuration = load_datasets_configuration(
        project_root=tmp_path,
        config_path="datasets.yaml",
    )
    core = configuration.get_dataset("core_ds")
    assert core.display_name == "Core"
    assert configuration.get_dataset("campaign_only").key == "campaign_only"
