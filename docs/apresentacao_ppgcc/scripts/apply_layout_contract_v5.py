#!/usr/bin/env python3
"""Compat: delega ao contrato v6 (altura real de conteúdo)."""

from __future__ import annotations

import apply_layout_contract_v7 as v7


def main() -> int:
    return v7.main()


if __name__ == "__main__":
    raise SystemExit(main())
