#!/usr/bin/env python3

"""
Executa inferência de sentimentos utilizando um modelo local
compatível com a biblioteca Transformers.

O modelo padrão do projeto é o FinBERT-PT-BR.

Fluxo:

1. Lê os argumentos recebidos pelo executar_finbert.sh.
2. Valida a pasta do modelo e o arquivo CSV.
3. Carrega o tokenizer e o modelo local.
4. Identifica CPU ou GPU.
5. Processa os textos em lotes.
6. Calcula as probabilidades das classes.
7. Calcula o índice contínuo:
   positivo - negativo.
8. Salva os resultados em CSV.
9. Salva os metadados da execução em JSON.

O parâmetro local_files_only=True garante que o Transformers
utilize somente os arquivos existentes na pasta do modelo.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import torch
import transformers
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)


# ============================================================
# ARGUMENTOS
# ============================================================

def parse_args() -> argparse.Namespace:
    """
    Define os parâmetros aceitos pela linha de comando.

    Retorna:
        argparse.Namespace:
            Valores informados pelo executar_finbert.sh ou terminal.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Classifica textos utilizando um modelo local "
            "compatível com Transformers."
        )
    )

    parser.add_argument(
        "--model-dir",
        required=True,
        help="Pasta local contendo o modelo e o tokenizer.",
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Arquivo CSV contendo os textos.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Arquivo CSV em que os resultados serão salvos.",
    )

    parser.add_argument(
        "--text-column",
        default="noticia",
        help="Nome da coluna que contém os textos.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Quantidade de textos processados simultaneamente.",
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Quantidade máxima de tokens por texto.",
    )

    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help=(
            "Dispositivo utilizado: auto, cpu ou cuda. "
            "Em auto, utiliza CUDA quando disponível."
        ),
    )

    return parser.parse_args()


# ============================================================
# VALIDAÇÃO DO MODELO
# ============================================================

def validar_arquivos_modelo(model_dir: Path) -> None:
    """
    Verifica se a pasta possui os arquivos mínimos para carregar
    um modelo local compatível com Transformers.

    São aceitos pesos nos formatos:

    - pytorch_model.bin;
    - model.safetensors;
    - pesos divididos em partes com arquivo de índice.

    Parâmetros:
        model_dir:
            Pasta local do modelo.
    """

    if not model_dir.is_dir():
        raise NotADirectoryError(
            f"Pasta do modelo não encontrada: {model_dir}"
        )

    config_path = model_dir / "config.json"

    if not config_path.is_file():
        raise FileNotFoundError(
            f"config.json não encontrado em: {model_dir}"
        )

    arquivos_pesos = [
        model_dir / "pytorch_model.bin",
        model_dir / "model.safetensors",
        model_dir / "pytorch_model.bin.index.json",
        model_dir / "model.safetensors.index.json",
    ]

    if not any(arquivo.is_file() for arquivo in arquivos_pesos):
        raise FileNotFoundError(
            "Nenhum arquivo de pesos foi encontrado na pasta do modelo. "
            "Formatos esperados: pytorch_model.bin ou model.safetensors."
        )

    arquivos_tokenizer = [
        model_dir / "tokenizer.json",
        model_dir / "vocab.txt",
        model_dir / "spiece.model",
        model_dir / "sentencepiece.bpe.model",
    ]

    if not any(
        arquivo.is_file()
        for arquivo in arquivos_tokenizer
    ):
        raise FileNotFoundError(
            "Nenhum arquivo de tokenizer foi encontrado "
            f"em: {model_dir}"
        )


# ============================================================
# CLASSES DE SENTIMENTO
# ============================================================

def obter_indices_classes(
    id2label: dict[int | str, str],
) -> tuple[dict[int, str], int, int, int]:
    """
    Localiza os índices das classes POSITIVE, NEGATIVE e NEUTRAL.

    A ordem das classes é lida da configuração do modelo, evitando
    assumir manualmente que positivo é sempre a classe zero.

    Parâmetros:
        id2label:
            Mapeamento entre índice e nome da classe.

    Retorna:
        tuple:
            Mapeamento das classes e índices de positivo,
            negativo e neutro.
    """

    labels = {
        int(indice): str(label).upper()
        for indice, label in id2label.items()
    }

    label2id = {
        label: indice
        for indice, label in labels.items()
    }

    classes_necessarias = {
        "POSITIVE",
        "NEGATIVE",
        "NEUTRAL",
    }

    if not classes_necessarias.issubset(label2id):
        raise ValueError(
            "O modelo precisa possuir as classes "
            "POSITIVE, NEGATIVE e NEUTRAL para calcular o índice. "
            f"Classes encontradas: {labels}"
        )

    return (
        labels,
        label2id["POSITIVE"],
        label2id["NEGATIVE"],
        label2id["NEUTRAL"],
    )


# ============================================================
# DISPOSITIVO
# ============================================================

def identificar_dispositivo(
    preferencia: str,
) -> torch.device:
    """
    Seleciona CPU ou GPU com base no parâmetro recebido.

    Parâmetros:
        preferencia:
            auto, cpu ou cuda.

    Retorna:
        torch.device:
            Dispositivo utilizado na inferência.
    """

    if preferencia == "cpu":
        return torch.device("cpu")

    if preferencia == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA foi solicitado, mas não está disponível."
            )

        return torch.device("cuda")

    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def obter_informacoes_dispositivo(
    device: torch.device,
) -> dict[str, Any]:
    """
    Reúne informações da CPU ou GPU utilizada.

    Os dados são gravados no arquivo de metadados.
    """

    info: dict[str, Any] = {
        "tipo": str(device),
        "cuda_disponivel": torch.cuda.is_available(),
        "gpu": None,
        "cuda_version": None,
        "memoria_maxima_gpu_mb": None,
    }

    if device.type == "cuda":
        info["gpu"] = torch.cuda.get_device_name(0)
        info["cuda_version"] = torch.version.cuda

    return info


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main() -> int:
    """
    Executa todas as etapas da inferência.

    Retorna:
        int:
            Zero quando a execução termina corretamente.
    """

    inicio_total = time.perf_counter()

    args = parse_args()

    model_dir = Path(
        args.model_dir
    ).expanduser().resolve()

    input_path = Path(
        args.input
    ).expanduser().resolve()

    output_path = Path(
        args.output
    ).expanduser().resolve()

    validar_arquivos_modelo(model_dir)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Arquivo de entrada não encontrado: {input_path}"
        )

    if args.batch_size <= 0:
        raise ValueError(
            "--batch-size deve ser maior que zero."
        )

    if args.max_length <= 0:
        raise ValueError(
            "--max-length deve ser maior que zero."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # LER O CSV
    # --------------------------------------------------------

    df = pd.read_csv(
        input_path,
        encoding="utf-8",
    )

    if args.text_column not in df.columns:
        raise KeyError(
            f"A coluna '{args.text_column}' não foi encontrada. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    textos_series = (
        df[args.text_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    indices_validos = textos_series[
        textos_series.str.len() > 0
    ].index.tolist()

    if not indices_validos:
        raise ValueError(
            "O CSV não contém textos válidos para processamento."
        )

    textos_validos = textos_series.loc[
        indices_validos
    ].tolist()

    # --------------------------------------------------------
    # DEFINIR DISPOSITIVO
    # --------------------------------------------------------

    device = identificar_dispositivo(
        args.device
    )

    device_info = obter_informacoes_dispositivo(
        device
    )

    # --------------------------------------------------------
    # CARREGAR TOKENIZER E MODELO
    # --------------------------------------------------------

    inicio_carregamento = time.perf_counter()

    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        model_dir,
        local_files_only=True,
    )

    limite_modelo = int(
        getattr(
            model.config,
            "max_position_embeddings",
            args.max_length,
        )
    )

    if args.max_length > limite_modelo:
        raise ValueError(
            f"O modelo aceita no máximo {limite_modelo} tokens, "
            f"mas --max-length recebeu {args.max_length}."
        )

    model.to(device)
    model.eval()

    tempo_carregamento = (
        time.perf_counter() - inicio_carregamento
    )

    (
        id2label,
        positive_index,
        negative_index,
        neutral_index,
    ) = obter_indices_classes(
        model.config.id2label
    )

    # --------------------------------------------------------
    # INFORMAÇÕES DO TESTE
    # --------------------------------------------------------

    print(f"Modelo: {model_dir.name}")
    print(f"Dispositivo utilizado: {device}")

    if device.type == "cuda":
        print(f"GPU: {device_info['gpu']}")

    print(f"Linhas no CSV: {len(df)}")
    print(f"Textos válidos: {len(textos_validos)}")
    print(f"Batch size: {args.batch_size}")
    print(f"Máximo de tokens: {args.max_length}")
    print(
        f"Tempo de carregamento: "
        f"{tempo_carregamento:.2f} segundos"
    )
    print()

    # --------------------------------------------------------
    # PREPARAR MEDIÇÃO DA INFERÊNCIA
    # --------------------------------------------------------

    resultados_por_indice: dict[
        int,
        dict[str, Any],
    ] = {}

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    inicio_inferencia = time.perf_counter()

    # --------------------------------------------------------
    # PROCESSAR EM LOTES
    # --------------------------------------------------------

    for inicio_lote in range(
        0,
        len(textos_validos),
        args.batch_size,
    ):
        fim_lote = min(
            inicio_lote + args.batch_size,
            len(textos_validos),
        )

        textos_lote = textos_validos[
            inicio_lote:fim_lote
        ]

        indices_lote = indices_validos[
            inicio_lote:fim_lote
        ]

        tokens = tokenizer(
            textos_lote,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=args.max_length,
        )

        tokens = {
            nome: tensor.to(device)
            for nome, tensor in tokens.items()
        }

        with torch.inference_mode():
            outputs = model(**tokens)

            probabilidades = torch.softmax(
                outputs.logits,
                dim=-1,
            ).cpu()

        for indice_df, probs in zip(
            indices_lote,
            probabilidades,
        ):
            positivo = float(
                probs[positive_index].item()
            )

            negativo = float(
                probs[negative_index].item()
            )

            neutro = float(
                probs[neutral_index].item()
            )

            classe_index = int(
                torch.argmax(probs).item()
            )

            confianca = float(
                probs[classe_index].item()
            )

            resultados_por_indice[indice_df] = {
                "sentimento": id2label[classe_index],
                "confianca": round(confianca, 6),
                "positivo": round(positivo, 6),
                "negativo": round(negativo, 6),
                "neutro": round(neutro, 6),
                "indice_sentimento": round(
                    positivo - negativo,
                    6,
                ),
            }

        print(
            f"Processados: "
            f"{fim_lote}/{len(textos_validos)}",
            flush=True,
        )

    if device.type == "cuda":
        torch.cuda.synchronize()

    tempo_inferencia = (
        time.perf_counter() - inicio_inferencia
    )

    # --------------------------------------------------------
    # ADICIONAR RESULTADOS AO DATAFRAME
    # --------------------------------------------------------

    df["sentimento"] = pd.Series(
        pd.NA,
        index=df.index,
        dtype="string",
    )

    colunas_numericas = [
        "confianca",
        "positivo",
        "negativo",
        "neutro",
        "indice_sentimento",
    ]

    for coluna in colunas_numericas:
        df[coluna] = float("nan")

    for indice_df, resultado in (
        resultados_por_indice.items()
    ):
        for coluna, valor in resultado.items():
            df.at[indice_df, coluna] = valor

    # --------------------------------------------------------
    # SALVAR CSV
    # --------------------------------------------------------

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # CRIAR METADADOS
    # --------------------------------------------------------

    tempo_total = (
        time.perf_counter() - inicio_total
    )

    textos_por_segundo = (
        len(textos_validos) / tempo_inferencia
        if tempo_inferencia > 0
        else None
    )

    if device.type == "cuda":
        memoria_gpu_mb = (
            torch.cuda.max_memory_allocated()
            / 1024
            / 1024
        )

        device_info[
            "memoria_maxima_gpu_mb"
        ] = round(memoria_gpu_mb, 2)

    metadata = {
        "modelo": {
            "nome": model_dir.name,
            "caminho": str(model_dir),
            "arquitetura": model.__class__.__name__,
            "classes": id2label,
        },
        "entrada": str(input_path),
        "saida": str(output_path),
        "coluna_texto": args.text_column,
        "quantidade_linhas": len(df),
        "quantidade_textos_validos": len(
            textos_validos
        ),
        "parametros": {
            "batch_size": args.batch_size,
            "max_length": args.max_length,
            "device_solicitado": args.device,
        },
        "dispositivo": device_info,
        "desempenho": {
            "tempo_carregamento_segundos": round(
                tempo_carregamento,
                4,
            ),
            "tempo_inferencia_segundos": round(
                tempo_inferencia,
                4,
            ),
            "tempo_total_segundos": round(
                tempo_total,
                4,
            ),
            "textos_por_segundo": (
                round(textos_por_segundo, 4)
                if textos_por_segundo is not None
                else None
            ),
        },
        "versoes": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "pandas": pd.__version__,
        },
    }

    metadata_path = output_path.with_suffix(
        ".metadata.json"
    )

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            metadata,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Resultado salvo em: {output_path}"
    )
    print(
        f"Metadados salvos em: {metadata_path}"
    )
    print(
        f"Tempo de inferência: "
        f"{tempo_inferencia:.2f} segundos"
    )
    print(
        f"Tempo total: {tempo_total:.2f} segundos"
    )

    if textos_por_segundo is not None:
        print(
            f"Velocidade: "
            f"{textos_por_segundo:.2f} textos/segundo"
        )

    return 0


# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except KeyboardInterrupt:
        print(
            "\nExecução interrompida pelo usuário.",
            file=sys.stderr,
        )
        raise SystemExit(130)

    except Exception as error:
        print(
            f"\nERRO: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)