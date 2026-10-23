"""Carrega e valida ``configs/campaigns/iti_v2/protocol.yaml``."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROTOCOL_ALLOWED_TOP = frozenset(
    {
        "protocol_version",
        "timezone",
        "index",
        "text",
        "temporal",
        "analysis",
        "legacy",
    }
)


class ProtocolError(ValueError):
    """Protocolo ITI-v2 inválido."""


@dataclass(frozen=True)
class ITIv2Protocol:
    path: Path
    raw: dict[str, Any]
    content_sha256: str

    @property
    def index_version(self) -> str:
        return str(self.raw.get("index", {}).get("version", ""))

    @property
    def half_life_days(self) -> tuple[int, ...]:
        values = self.raw.get("index", {}).get("half_life_days", [])
        return tuple(int(v) for v in values)

    @property
    def warmup_days(self) -> int:
        return int(self.raw.get("index", {}).get("warmup_days", 70))

    @property
    def week_anchor(self) -> str:
        return str(self.raw.get("temporal", {}).get("week_anchor", "W-FRI"))


def load_iti_v2_protocol(path: Path) -> ITIv2Protocol:
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ProtocolError("protocol.yaml precisa ser um objeto.")

    unknown = set(raw) - PROTOCOL_ALLOWED_TOP
    if unknown:
        raise ProtocolError(f"Campos de topo desconhecidos: {sorted(unknown)}")

    if raw.get("index", {}).get("version") != "iti_v2":
        raise ProtocolError("index.version precisa ser iti_v2 para esta campanha.")

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ITIv2Protocol(path=path, raw=raw, content_sha256=digest)


def write_resolved_protocol(protocol: ITIv2Protocol, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "protocol_resolved.json"
    payload = {
        "source": str(protocol.path),
        "content_sha256": protocol.content_sha256,
        "protocol": protocol.raw,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
