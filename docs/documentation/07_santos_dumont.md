# 07 Santos Dumont

## 7. Apêndice — execução no Santos Dumont (desenvolvimento)

O cluster SDumont é um **ambiente de teste HPC** para rodar o experimento com GPU; não faz parte do desenho científico em si. O job Slurm executa `./scripts/run_experiment.sh --skip-setup` (sem scraper nem research no nó). Fluxo local equivalente: [11_end_to_end_flow](11_end_to_end_flow.md).

Este capítulo descreve o fluxo **manual**: VPN, SSH no login, comandos no scratch. Não cobre automação local (scripts externos ao repositório).

### 7.1 Visão geral

```text
[PC]  git push
[Login SDumont]  git pull / reset --hard origin/main
[Login SDumont]  module load cuda + anaconda (setup, se necessário)
[Login SDumont]  ./scripts/audit_project.sh --sdumont   # preferir em job GPU
[Login SDumont]  sbatch jobs/sdumont/run_experiment.srm
[Login SDumont]  squeue / sacct / tail do log Slurm
[PC]  scp outputs/ e logs/
[PC]  ./scripts/run_research.sh --run-id <run_id>
```

### 7.2 Acesso e caminhos

1. Conecte a **VPN institucional** LNCC (SDumont).
2. Abra um terminal no seu PC e entre no login:

```bash
ssh -o MACs=hmac-sha2-256 -o Ciphers=aes256-ctr \
    <usuario>@login.sdumont.lncc.br
```

| Variável | Exemplo |
| --- | --- |
| `$HOME` | `/prj/ufsj/hpc4agents-br/<usuario>` |
| `$SCRATCH` | `/scratch/ufsj/hpc4agents-br/<usuario>` |
| Projeto | `$SCRATCH/financial-sentiment-lab` |

**Primeiro clone** (uma vez):

```bash
mkdir -p "$SCRATCH"
cd "$SCRATCH"
git clone https://github.com/<org>/Financial-Sentiment-Lab.git financial-sentiment-lab
cd financial-sentiment-lab
```

### 7.3 Setup no nó de login

No **login**, use módulos da fila Sequana (não use `arch_gpu/current` aqui nem nos jobs `sequana_gpu_dev`):

```bash
cd "$SCRATCH/financial-sentiment-lab"
module purge
module load cuda/12.6_sequana
module load anaconda3/2024.02_sequana

./scripts/setup_env.sh --fetch-assets

source venv/bin/activate
pip uninstall -y torch
pip install torch --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

`torch.cuda.is_available()` pode ser **falso** no login; CUDA vale no **nó GPU** após o `sbatch` alocar recurso.

### 7.4 Atualizar código

Edite no PC → `git push`. No cluster:

```bash
cd "$SCRATCH/financial-sentiment-lab"
git fetch origin
git reset --hard origin/main
```

Não faça `git push` a partir do SDumont.

### 7.5 Validar antes do job

`audit_project.sh --sdumont` omite testes marcados `sdumont` (dashboard com `outputs/` locais). Rode `./scripts/audit_project.sh` **completo no PC** antes do `git push`.

No cluster, o audit com checagem CUDA deve rodar em **nó GPU** (por exemplo dentro do mesmo fluxo que já submete o experimento, ou via `srun`/`sbatch` com `--gres=gpu:1` na partição `sequana_gpu_dev`). No login, a seção de integração CUDA pode falhar — isso é esperado.

```bash
cd "$SCRATCH/financial-sentiment-lab"
source venv/bin/activate
./scripts/audit_project.sh --sdumont
```

### 7.6 Submeter o experimento

Job padrão: [`jobs/sdumont/run_experiment.srm`](../../jobs/sdumont/run_experiment.srm) — partição `sequana_gpu_dev`, ~20 min, 1 GPU. Campanha **Sabesp R1** (`sabesp_2026` / `r1_alpha070`); `run_id` esperado: **`sabesp_r1_alpha070`**.

```bash
cd "$SCRATCH/financial-sentiment-lab"
sbatch jobs/sdumont/run_experiment.srm
```

Anote o número retornado (`Submitted batch job 12345678`).

```bash
squeue -u "$USER"
```

### 7.7 Acompanhar logs

| O quê | Onde |
| --- | --- |
| Saída Slurm | `$SCRATCH/financial-sentiment-lab/job_financial_<JOBID>.out` |
| Log da pipeline | `logs/sabesp_r1_alpha070.log` |
| Relatório audit | `logs/audit/audit_project_*.log` |

Enquanto o job roda ou após terminar:

```bash
sacct -j <JOBID> --format=JobID,JobName,State,ExitCode,Elapsed,End
tail -f job_financial_<JOBID>.out
```

O `.srm` envia stdout e stderr para o mesmo `job_financial_<JOBID>.out`. Jobs antigos podem ter ainda um `.err` separado.

Confirme sucesso no log: `Experimento concluído` e `sacct` com `State=COMPLETED`, `ExitCode 0:0`.

### 7.8 Baixar resultados (PC)

Com VPN ativa, no **PowerShell** ou terminal com `scp` (ajuste usuário e `JOB`):

```powershell
$SSH = "-o MACs=hmac-sha2-256 -o Ciphers=aes256-ctr -o IPQoS=none -o Compression=no"
$BASE = "<usuario>@login.sdumont.lncc.br:/scratch/ufsj/hpc4agents-br/<usuario>/financial-sentiment-lab"
$JOB = "12345678"

scp -r $SSH "${BASE}/outputs/sabesp_r1_alpha070" .
scp $SSH "${BASE}/logs/sabesp_r1_alpha070.log" .
scp $SSH "${BASE}/job_financial_${JOB}.out" .
```

### 7.9 Research no PC

O job HPC **não** executa `modules.research`. Após baixar `outputs/`:

```bash
cd /caminho/local/Financial-Sentiment-Lab
./scripts/run_research.sh --run-id sabesp_r1_alpha070
```

Validação completa (mercado, scraper, etc.) permanece no ambiente local — ver [7.10](#710-research-e-scraper-fora-do-job-padrão).

### 7.10 Research e scraper fora do job padrão

```bash
python -m modules.market fetch
python -m modules.research validate --run-id sabesp_r1_alpha070
```

### 7.11 Problemas comuns

| Sintoma | Solução |
| --- | --- |
| `arch_gpu/current` unknown | Na fila Sequana use só `cuda/12.6_sequana` + anaconda (como no `.srm` atual) |
| Audit CUDA falha no login | Normal no login; rode audit com GPU alocada ou confie no job `sbatch` |
| `Failed building wheel for pyarrow` | `rm -rf venv && ./scripts/setup_env.sh --recreate --fetch-assets` |
| `bad interpreter` no venv | Recriar venv + setup + PyTorch cu124 |
| CUDA driver too old | Reinstalar torch com index `cu124` |
| Quota SCRATCH | Limpar `outputs/` antigos e `job_financial_*.out` |
| Job `FAILED` em segundos | `sacct -j ID`; `tail` do `.out` / `.err`; módulos Lmod no nó GPU |

---
