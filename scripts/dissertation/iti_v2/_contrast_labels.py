"""Rótulos públicos em português para contrastes ITI-v2 (dissertação)."""

from __future__ import annotations

CONTRAST_LABELS_PT: dict[str, str] = {
    "PRIMARY_DELTA_H7_SOFT": "ITI-H7 × Soft ($h=1$)",
    "SEC_H2_VS_SOFT": "Memória $H=2$ × Soft",
    "SEC_H14_VS_SOFT": "Memória $H=14$ × Soft",
    "SEC_H7_VS_SOFT_PEARSON": "Pearson, $H=7$",
    "SEC_H7_VS_SOFT_H2": "Retorno $h=2$ semanas",
    "SEC_H7_VS_SOFT_H4": "Retorno $h=4$ semanas",
    "SEC_H7_VS_HARD": "ITI-H7 × escore discreto",
    "SEC_CONTEXT_VS_DOCUMENT_H7": "Contexto focal × texto integral",
    "SEC_H7_VS_LEGACY_C": "ITI-H7 × suavização alternativa",
}


def label_for(contrast_id: str) -> str:
    return CONTRAST_LABELS_PT.get(contrast_id, contrast_id.replace("_", r"\_"))
