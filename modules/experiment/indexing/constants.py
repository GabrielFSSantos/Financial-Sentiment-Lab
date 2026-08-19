"""Constantes compartilhadas do ITI."""

DIMENSION_KEYS: tuple[str, ...] = (
    "magnitude",
    "relevance",
    "event_weight",
    "horizon",
    "risk",
    "novelty",
)

DIMENSION_SHORT_NAMES: dict[str, str] = {
    "magnitude": "m",
    "relevance": "r",
    "event_weight": "e",
    "horizon": "h",
    "risk": "q",
    "novelty": "u",
}
