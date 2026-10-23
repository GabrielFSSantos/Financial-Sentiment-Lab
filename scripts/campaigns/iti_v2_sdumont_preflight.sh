#!/usr/bin/env bash
# Gate local antes de sbatch ITI-v2 — tudo exceto execução no nó GPU.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${ROOT}/venv/bin/python"
CORPUS="${ITI_V2_CORPUS_DIR:-outputs/corpus_inventory/iti_v2_p02}"
REF_RUN="${ITI_V2_REF_RUN:-iti_v2_prod_20261022}"
FAIL=0

echo "=== ITI-v2 SDumont preflight ==="
echo "ROOT=$ROOT"
echo "REF_RUN=$REF_RUN (referência local; no cluster use ITI_RUN_ID novo)"
echo ""

_require() {
  if [[ -f "$1" ]]; then
    echo "[OK] $2"
  else
    echo "[FALHA] $2 — ausente: $1"
    FAIL=1
  fi
}

_require "model_store/FinBERT-PT-BR/pytorch_model.bin" "FinBERT local"
_require "data/water_utilities_corpus/articles_strict_sabesp.csv" "corpus fonte"
_require "$CORPUS/protocol_lock.json" "protocol_lock"
_require "$CORPUS/articles_canonical.csv" "corpus canônico P02"
_require "$CORPUS/split_manifest.json" "split_manifest"
_require "outputs/campaigns/iti_v2/env_lock/requirements-frozen.txt" "env lock (rode: iti_v2.sh pin-env)"
_require "jobs/sdumont/run_iti_v2.srm" "job Slurm"
_require "configs/campaigns/iti_v2/protocol.yaml" "protocol.yaml"

if bash -n "$ROOT/scripts/campaigns/iti_v2.sh" && bash -n "$ROOT/jobs/sdumont/run_iti_v2.srm"; then
  echo "[OK] bash -n scripts"
else
  echo "[FALHA] sintaxe shell"
  FAIL=1
fi

echo ""
echo "=== Validação campanha (referência local) ==="
if "$ROOT/scripts/campaigns/iti_v2.sh" validate "$REF_RUN"; then
  echo "[OK] validate $REF_RUN"
else
  echo "[AVISO] validate falhou — no cluster, valide após o job com o novo run_id"
fi

echo ""
echo "=== Submissão no login SDumont (copiar) ==="
cat <<EOF
export ITI_PROJECT_DIR="\$SCRATCH/financial-sentiment-lab"   # ajuste se necessário
export ITI_RUN_ID="iti_v2_sdumont_\$(date +%Y%m%d)"
export ITI_V2_INFER_LIMIT=0
export ITI_V2_BOOTSTRAP=10000
cd "\$ITI_PROJECT_DIR"
git fetch origin && git reset --hard origin/main   # ou commit fixo do protocol_lock
./scripts/campaigns/iti_v2.sh pin-env              # no cluster, após venv+torch CUDA
./scripts/campaigns/iti_v2.sh prepare              # se corpus P02 não sincronizado
./scripts/campaigns/iti_v2.sh select-holdout 12
./scripts/campaigns/iti_v2.sh lock-protocol
sbatch jobs/sdumont/run_iti_v2.srm
EOF

if [[ "$FAIL" -ne 0 ]]; then
  echo ""
  echo "Preflight FALHOU — corrija antes do SDumont."
  exit 1
fi
echo ""
echo "Preflight OK — único passo pendente: sbatch no SDumont."
exit 0
