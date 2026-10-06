"""Fixed prompts for label judges (qualification pilot)."""

from __future__ import annotations

PROMPT_V1_QUALI = """Você avalia o impacto de uma notícia financeira/jornalística APENAS para a empresa-alvo: Sabesp (saneamento, Brasil).

Classes (responda exatamente uma): POSITIVE, NEGATIVE, NEUTRAL.

- POSITIVE: fato favorável à Sabesp.
- NEGATIVE: fato desfavorável à Sabesp.
- NEUTRAL: sem efeito claro para a Sabesp, ou menção tangencial.

Se a matéria menciona várias empresas, ignore o tom geral do mercado e julgue só a Sabesp.

Responda em duas linhas:
CLASSE: <POSITIVE|NEGATIVE|NEUTRAL>
JUSTIFICATIVA: <uma frase curta em português>

Título: {title}
Texto: {text}
"""


def format_prompt_v1_quali(title: str, text: str) -> str:
    return PROMPT_V1_QUALI.format(title=title.strip(), text=text.strip())
