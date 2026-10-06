"""Utilitários compartilhados do runner (sem dependência circular)."""

from __future__ import annotations

import gc

import torch


def release_python_and_cuda_memory() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        try:
            torch.cuda.ipc_collect()
        except RuntimeError:
            pass


def format_combination_progress(current: int, total: int) -> str:
    if total <= 0:
        return "0/0 combinações (0%)"

    percentage = int(round(100 * current / total))
    return f"{current}/{total} combinações ({percentage}%)"
