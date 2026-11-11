#!/usr/bin/env python3
"""Hash estável dos campos de roteiro protegidos (voice, transition, …)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dados" / "manifesto_slides.json"
OUT = ROOT / "build" / "roteiro_protegido.sha"

PROTECTED = ("voice", "transition", "pointing", "objective", "seconds")


def payload(manifest: dict) -> list[dict]:
    blocks: list[dict] = []
    for section in ("slides", "backup"):
        for slide in manifest.get(section, []):
            blocks.append(
                {
                    "id": slide.get("id"),
                    "section": section,
                    **{k: slide.get(k) for k in PROTECTED},
                }
            )
    return sorted(blocks, key=lambda b: (b["section"], b["id"] or ""))


def compute_hash(manifest: dict) -> str:
    raw = json.dumps(payload(manifest), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Grava hash em build/roteiro_protegido.sha")
    parser.add_argument("--verify", action="store_true", help="Compara com hash gravado")
    parser.add_argument("--print", action="store_true", help="Imprime hash na stdout")
    args = parser.parse_args()

    if not MANIFEST.is_file():
        print(f"ERRO: manifesto ausente: {MANIFEST}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    digest = compute_hash(manifest)

    if args.print or (not args.write and not args.verify):
        print(digest)
        return 0

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(digest + "\n", encoding="utf-8")
        print(f"OK: hash gravado em {OUT.relative_to(ROOT)}")
        print(digest)

    if args.verify:
        if not OUT.is_file():
            print("ERRO: execute --write antes de --verify", file=sys.stderr)
            return 1
        saved = OUT.read_text(encoding="utf-8").strip()
        if saved != digest:
            print(f"ERRO: hash do roteiro alterado\n  esperado: {saved}\n  atual:    {digest}", file=sys.stderr)
            return 1
        print("OK: campos protegidos inalterados")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
