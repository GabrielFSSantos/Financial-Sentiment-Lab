"""Parse judge model text into label + rationale."""

from __future__ import annotations

import re

_VALID = frozenset({"POSITIVE", "NEGATIVE", "NEUTRAL"})


def parse_classe_justificativa(raw: str) -> tuple[str, str]:
    """Extract POSITIVE|NEGATIVE|NEUTRAL and short rationale from model output."""
    text = raw.strip()
    label = ""
    rationale = ""

    classe_match = re.search(
        r"CLASSE:\s*(POSITIVE|NEGATIVE|NEUTRAL)",
        text,
        flags=re.IGNORECASE,
    )
    if classe_match:
        label = classe_match.group(1).upper()

    just_match = re.search(
        r"JUSTIFICATIVA:\s*(.+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if just_match:
        rationale = just_match.group(1).strip().splitlines()[0].strip()

    if not label:
        for token in _VALID:
            if token in text.upper():
                label = token
                break

    if not rationale:
        rationale = text[:200].replace("\n", " ")

    if label not in _VALID:
        raise ValueError(f"Resposta do juiz sem classe válida: {raw[:120]!r}")

    return label, rationale
