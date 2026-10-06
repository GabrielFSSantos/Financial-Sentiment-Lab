#!/usr/bin/env bash
# Baixa PDFs de acesso aberto para docs/references/pdfs/
# Uso: ./scripts/download_references.sh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/docs/references/pdfs"
LOG="$DEST/download.log"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
FAILED=0

mkdir -p "$DEST"
: > "$LOG"

download_pdf() {
  local name="$1"
  local url="$2"
  local out="$DEST/$name"
  local tmp="${out}.part"

  if [[ -f "$out" ]]; then
    echo "==> $name" | tee -a "$LOG"
    echo "    SKIP: already exists ($(wc -c < "$out") bytes)" | tee -a "$LOG"
    return 0
  fi

  echo "==> $name" | tee -a "$LOG"
  echo "    URL: $url" >> "$LOG"

  if curl -fsSL -A "$UA" -L --max-time 120 -o "$tmp" "$url" 2>>"$LOG"; then
    if file -b "$tmp" | grep -qi 'pdf'; then
      mv "$tmp" "$out"
      echo "    OK: $(wc -c < "$out") bytes" | tee -a "$LOG"
      return 0
    fi
    echo "    FAIL: not PDF ($(file -b "$tmp"))" | tee -a "$LOG"
    rm -f "$tmp"
  else
    echo "    FAIL: curl error" | tee -a "$LOG"
    rm -f "$tmp"
  fi
  FAILED=$((FAILED + 1))
  return 1
}

# SBC BWAIF — FinBERT-PT-BR
download_pdf "santos2023_finbert_ptbr.pdf" \
  "https://sol.sbc.org.br/index.php/bwaif/article/download/24960/16609" || true

# ERAMIARS 2025
download_pdf "marquezan2025_eramiars.pdf" \
  "https://sol.sbc.org.br/index.php/eramiars/article/download/16502/16403" || true

# FOCO — privatização Sabesp
download_pdf "gattai2025_privatizacao_sabesp.pdf" \
  "https://ojs.focopublicacoes.com.br/foco/article/download/12166/8493" || true

# SciELO — Yoshinaga 2012 BAR
download_pdf "yoshinaga2012_bar.pdf" \
  "https://www.scielo.br/pdf/bar/v9n4/1807-7692-bar-9-04-00390.pdf" || true

# arXiv — FinBERT EN
download_pdf "araci2020_finbert.pdf" \
  "https://arxiv.org/pdf/1908.10063.pdf" || true

# RACEf — página DOI (pode redirecionar para HTML)
download_pdf "racef2022_sentimento.pdf" \
  "https://doi.org/10.13059/racef.v13i3.985" || true

# UTFPR — repositório (pode exigir interação)
download_pdf "utfpr2024_noticias_acoes.pdf" \
  "http://repositorio.utfpr.edu.br/jspui/bitstream/1/40390/1/UTFPR%20BERT%20noticias.pdf" || true

# WebMedia / SBC — Neuenschwander 2014 (repositório USP comum)
download_pdf "neuenschwander2014_webmedia.pdf" \
  "https://www.researchgate.net/profile/Rafael-Neuenschwander/publication/267749000_Sentiment_Analysis_for_Streams_of_Web_Data_A_Case_Study_of_Brazilian_Financial_Markets/links/545a3e0e0cf26d5090a3c8c0/Sentiment-Analysis-for-Streams-of-Web-Data-A-Case-Study-of-Brazilian-Financial-Markets.pdf" || true

echo "" | tee -a "$LOG"
if [[ "$FAILED" -gt 0 ]]; then
  echo "Concluído com $FAILED falha(s). Ver $LOG" | tee -a "$LOG"
  echo "Artigos pagos (Duarte 2020, BERTimbau, Tetlock): usar apenas metadados em bibliografia.bib"
  exit 1
fi
echo "Todos os downloads OK." | tee -a "$LOG"
exit 0
