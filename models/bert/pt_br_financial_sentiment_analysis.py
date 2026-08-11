#!/usr/bin/env python3

"""Adaptador local do ensemble financeiro PT-BR de Lucas Almeida.

O modelo publicado em ``lucasalmda/pt-br-financial-sentiment-analysis``
possui três checkpoints. Conforme a model card, a inferência oficial do
ensemble calcula a média dos logits de ``seed-789``, ``seed-123`` e
``seed-456`` antes de selecionar a classe. Este adaptador preserva esse
procedimento e aplica softmax somente aos logits médios para atender ao
contrato probabilístico da pipeline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import torch
import transformers
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from models.base_model import (
    BaseSentimentModel,
    ModelConfigurationError,
    ModelLoadingError,
    ModelPrediction,
    ModelPredictionError,
)
from models.bert.finbert_ptbr import FinBertPtBrModel

if TYPE_CHECKING:
    from pipeline.configuration import ModelConfiguration


DEFAULT_MODEL_NAME = "pt_br_financial_sentiment_analysis"
DEFAULT_CHECKPOINT_DIRECTORIES: tuple[str, ...] = (
    "seed-789",
    "seed-123",
    "seed-456",
)
REQUIRED_CHECKPOINT_FILES: tuple[str, ...] = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)
TOKENIZER_FILES: tuple[str, ...] = (
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)
GIT_LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


class PtBrFinancialSentimentAnalysisModel(FinBertPtBrModel):
    """Executa o ensemble dos três checkpoints financeiros PT-BR."""

    def __init__(
        self,
        model_dir: str | Path,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = 32,
        max_length: int = 512,
        device: str = "auto",
        checkpoint_directories: Sequence[str] = DEFAULT_CHECKPOINT_DIRECTORIES,
        model_configuration: "ModelConfiguration | None" = None,
        loading: Mapping[str, Any] | None = None,
        validation: Mapping[str, Any] | None = None,
    ) -> None:
        """Inicializa o ensemble sem carregar os três checkpoints."""

        super().__init__(
            model_dir=model_dir,
            model_name=model_name,
            batch_size=batch_size,
            max_length=max_length,
            device=device,
            probability_function="softmax",
            model_configuration=model_configuration,
            loading=loading,
            validation=validation,
        )

        self.checkpoint_directories = (
            self._normalize_checkpoint_directories(
                checkpoint_directories
            )
        )
        self.validate_identical_tokenizers = (
            self._configuration_boolean(
                self.validation_configuration,
                "validate_identical_tokenizers",
                default=True,
            )
        )
        self.reject_git_lfs_pointers = self._configuration_boolean(
            self.validation_configuration,
            "reject_git_lfs_pointers",
            default=True,
        )

        self.models: list[Any] = []
        self.checkpoint_configurations: dict[
            str,
            dict[str, Any],
        ] = {}
        self.checkpoint_problem_types: dict[str, str | None] = {}
        self.checkpoint_architectures: dict[str, str] = {}

    @staticmethod
    def _normalize_checkpoint_directories(
        values: Sequence[str],
    ) -> tuple[str, ...]:
        """Valida nomes relativos, únicos e não vazios de checkpoints."""

        if isinstance(values, (str, bytes)):
            raise ModelConfigurationError(
                "checkpoint_directories precisa ser uma lista."
            )

        try:
            raw_values = tuple(values)
        except TypeError as error:
            raise ModelConfigurationError(
                "checkpoint_directories precisa ser iterável."
            ) from error

        if not raw_values:
            raise ModelConfigurationError(
                "checkpoint_directories não pode ficar vazio."
            )

        normalized: list[str] = []

        for raw_value in raw_values:
            value = str(raw_value).strip()
            relative_path = Path(value)

            if (
                not value
                or relative_path.is_absolute()
                or len(relative_path.parts) != 1
                or value in {".", ".."}
            ):
                raise ModelConfigurationError(
                    "Cada checkpoint precisa ser o nome de uma pasta "
                    f"relativa simples. Valor recebido: {raw_value!r}."
                )

            normalized.append(value)

        if len(set(normalized)) != len(normalized):
            raise ModelConfigurationError(
                "checkpoint_directories possui valores duplicados."
            )

        return tuple(normalized)

    @property
    def checkpoint_paths(self) -> tuple[Path, ...]:
        """Retorna os caminhos absolutos dos checkpoints configurados."""

        return tuple(
            self.model_dir / directory
            for directory in self.checkpoint_directories
        )

    def validate_model_files(self) -> None:
        """Valida os três checkpoints e a consistência do ensemble."""

        if not self.model_dir.exists():
            raise FileNotFoundError(
                "Pasta do ensemble financeiro PT-BR não encontrada: "
                f"{self.model_dir}"
            )

        if not self.model_dir.is_dir():
            raise NotADirectoryError(
                "O caminho do ensemble financeiro PT-BR não é uma "
                f"pasta: {self.model_dir}"
            )

        self._validate_training_strategy()

        reference_config: dict[str, Any] | None = None
        reference_tokenizer_hashes: dict[str, str] | None = None
        checkpoint_configurations: dict[str, dict[str, Any]] = {}
        detected_weights: list[str] = []
        detected_tokenizers: list[str] = []

        for directory, checkpoint_path in zip(
            self.checkpoint_directories,
            self.checkpoint_paths,
        ):
            if not checkpoint_path.is_dir():
                raise FileNotFoundError(
                    f"Checkpoint {directory!r} não encontrado em "
                    f"{checkpoint_path}."
                )

            missing = [
                filename
                for filename in REQUIRED_CHECKPOINT_FILES
                if not (checkpoint_path / filename).is_file()
            ]

            if missing:
                formatted = ", ".join(missing)
                raise FileNotFoundError(
                    f"Checkpoint {directory!r} possui arquivos "
                    f"ausentes: {formatted}."
                )

            weight_path = checkpoint_path / "model.safetensors"
            self._validate_weight_payload(weight_path)

            config_data = self._read_json_object(
                checkpoint_path / "config.json",
                description=f"{directory}/config.json",
            )
            self._validate_config_data(config_data)

            if reference_config is None:
                reference_config = config_data
            else:
                self._validate_compatible_configurations(
                    reference_config,
                    config_data,
                    directory,
                )

            tokenizer_hashes = {
                filename: self._sha256(checkpoint_path / filename)
                for filename in TOKENIZER_FILES
            }

            if reference_tokenizer_hashes is None:
                reference_tokenizer_hashes = tokenizer_hashes
            elif (
                self.validate_identical_tokenizers
                and tokenizer_hashes != reference_tokenizer_hashes
            ):
                raise ModelConfigurationError(
                    f"O tokenizer de {directory!r} diverge dos demais "
                    "checkpoints do ensemble."
                )

            checkpoint_configurations[directory] = config_data
            detected_weights.append(
                f"{directory}/model.safetensors"
            )
            detected_tokenizers.extend(
                f"{directory}/{filename}"
                for filename in TOKENIZER_FILES
            )

        if reference_config is None:
            raise ModelConfigurationError(
                "Nenhum config.json foi validado para o ensemble."
            )

        self.model_config_data = reference_config
        self.checkpoint_configurations = checkpoint_configurations
        self.detected_weight_files = tuple(detected_weights)
        self.detected_tokenizer_files = tuple(detected_tokenizers)
        self.detected_shard_files = tuple()

    def _validate_training_strategy(self) -> None:
        """Confere se os checkpoints correspondem ao ensemble publicado."""

        strategy_path = self.model_dir / "training_strategy.json"

        if not strategy_path.is_file():
            raise FileNotFoundError(
                f"training_strategy.json não encontrado em {self.model_dir}."
            )

        strategy = self._read_json_object(
            strategy_path,
            description="training_strategy.json",
        )

        if strategy.get("ensemble_mode") is not True:
            raise ModelConfigurationError(
                "training_strategy.json não declara ensemble_mode=true."
            )

        raw_seeds = strategy.get("ensemble_seeds")

        if not isinstance(raw_seeds, list):
            raise ModelConfigurationError(
                "training_strategy.json não possui ensemble_seeds válido."
            )

        strategy_directories = tuple(
            f"seed-{self._parse_non_negative_integer(seed, 'ensemble_seed')}"
            for seed in raw_seeds
        )

        if (
            len(strategy_directories)
            != len(self.checkpoint_directories)
            or set(strategy_directories)
            != set(self.checkpoint_directories)
        ):
            raise ModelConfigurationError(
                "Os checkpoints configurados divergem de "
                "training_strategy.json. "
                f"configurados={self.checkpoint_directories}; "
                f"estratégia={strategy_directories}."
            )

    def _validate_weight_payload(self, path: Path) -> None:
        """Rejeita ponteiros Git LFS ainda não materializados."""

        if not self.reject_git_lfs_pointers:
            return

        try:
            with path.open("rb") as file:
                header = file.read(len(GIT_LFS_POINTER_PREFIX))
        except OSError as error:
            raise ModelConfigurationError(
                f"Não foi possível ler o peso {path}: {error}"
            ) from error

        if header == GIT_LFS_POINTER_PREFIX:
            raise FileNotFoundError(
                f"{path} ainda é um ponteiro Git LFS. Baixe o conteúdo "
                "real dos pesos antes de executar a inferência."
            )

    @staticmethod
    def _sha256(path: Path) -> str:
        """Calcula o hash de um arquivo pequeno de configuração."""

        digest = hashlib.sha256()

        try:
            with path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as error:
            raise ModelConfigurationError(
                f"Não foi possível calcular o hash de {path}: {error}"
            ) from error

        return digest.hexdigest()

    @staticmethod
    def _validate_compatible_configurations(
        reference: Mapping[str, Any],
        candidate: Mapping[str, Any],
        checkpoint_name: str,
    ) -> None:
        """Exige configurações compatíveis para a média dos logits."""

        required_equal_fields = (
            "model_type",
            "architectures",
            "id2label",
            "label2id",
            "num_labels",
            "max_position_embeddings",
            "vocab_size",
            "problem_type",
        )

        divergent = [
            field
            for field in required_equal_fields
            if reference.get(field) != candidate.get(field)
        ]

        if divergent:
            raise ModelConfigurationError(
                f"O checkpoint {checkpoint_name!r} possui configuração "
                "incompatível com o ensemble nos campos: "
                f"{divergent}."
            )

    def _load_model(self) -> None:
        """Carrega um tokenizer comum e os três modelos locais."""

        tokenizer_arguments: dict[str, Any] = {
            "local_files_only": self.local_files_only,
            "trust_remote_code": self.trust_remote_code,
            "use_fast": self.use_fast_tokenizer,
        }
        model_arguments: dict[str, Any] = {
            "local_files_only": self.local_files_only,
            "trust_remote_code": self.trust_remote_code,
            "use_safetensors": True,
        }

        if self.use_safetensors is False:
            raise ModelConfigurationError(
                "O ensemble publicado utiliza pesos safetensors; "
                "loading.use_safetensors não pode ser false."
            )

        loaded_models: list[Any] = []
        checkpoint_problem_types: dict[str, str | None] = {}
        checkpoint_architectures: dict[str, str] = {}

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                str(self.checkpoint_paths[0]),
                **tokenizer_arguments,
            )

            for directory, checkpoint_path in zip(
                self.checkpoint_directories,
                self.checkpoint_paths,
            ):
                model = (
                    AutoModelForSequenceClassification.from_pretrained(
                        str(checkpoint_path),
                        **model_arguments,
                    )
                )

                loaded_id2label = getattr(
                    model.config,
                    "id2label",
                    None,
                )

                if not isinstance(loaded_id2label, Mapping):
                    raise ModelLoadingError(
                        f"O checkpoint {directory!r} não possui "
                        "id2label válido."
                    )

                self._configure_class_indices(
                    loaded_id2label,
                    source=f"{directory}.model.config",
                )
                self._validate_labels_against_models_yaml()

                loaded_max_length = self._parse_positive_integer(
                    getattr(
                        model.config,
                        "max_position_embeddings",
                        None,
                    ),
                    f"{directory}.max_position_embeddings",
                )

                if self.max_length > loaded_max_length:
                    raise ModelLoadingError(
                        f"O checkpoint {directory!r} aceita no máximo "
                        f"{loaded_max_length} tokens."
                    )

                problem_type_value = getattr(
                    model.config,
                    "problem_type",
                    None,
                )
                checkpoint_problem_types[directory] = (
                    str(problem_type_value).strip()
                    if problem_type_value is not None
                    else None
                )

                model.to(self.device)
                model.eval()
                loaded_models.append(model)
                checkpoint_architectures[directory] = (
                    model.__class__.__name__
                )
        except Exception as error:
            loaded_models.clear()

            if isinstance(error, (ModelLoadingError, ModelConfigurationError)):
                raise

            raise ModelLoadingError(
                "Falha ao carregar o ensemble financeiro PT-BR em "
                f"{self.model_dir}: {error}"
            ) from error

        self.tokenizer = tokenizer
        self.models = loaded_models
        self.model = self.models
        self.checkpoint_problem_types = checkpoint_problem_types
        self.checkpoint_architectures = checkpoint_architectures
        self.loaded_problem_type = "single_label_classification"
        self.resolved_probability_function = "softmax"
        self.score_normalization = "none"
        self._architecture_name = (
            f"BertForSequenceClassificationEnsemble[{len(self.models)}]"
        )

    def _predict_batch(
        self,
        texts: Sequence[str],
    ) -> list[ModelPrediction]:
        """Calcula a média dos logits antes do softmax e do argmax."""

        if not self.models:
            raise ModelPredictionError(
                "Os checkpoints do ensemble ainda não foram carregados."
            )

        if self.tokenizer is None:
            raise ModelPredictionError(
                "O tokenizer do ensemble ainda não foi carregado."
            )

        if not texts:
            return []

        try:
            encoded_inputs = self.tokenizer(
                list(texts),
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length,
            )
        except Exception as error:
            raise ModelPredictionError(
                f"Falha durante a tokenização: {error}"
            ) from error

        attention_mask_value = encoded_inputs.get("attention_mask")
        attention_mask = (
            attention_mask_value
            if isinstance(attention_mask_value, torch.Tensor)
            else None
        )
        token_counts = self._extract_token_counts(
            attention_mask,
            len(texts),
        )
        model_inputs: dict[str, torch.Tensor] = {}

        for input_name, input_value in encoded_inputs.items():
            if not isinstance(input_value, torch.Tensor):
                raise ModelPredictionError(
                    "O tokenizer retornou valor não tensor para "
                    f"{input_name!r}."
                )

            model_inputs[str(input_name)] = input_value.to(self.device)

        self._synchronize_cuda()
        logits_by_checkpoint: list[torch.Tensor] = []

        try:
            with torch.inference_mode():
                for directory, model in zip(
                    self.checkpoint_directories,
                    self.models,
                ):
                    outputs = model(**model_inputs)
                    logits = getattr(outputs, "logits", None)

                    if not isinstance(logits, torch.Tensor):
                        raise ModelPredictionError(
                            f"O checkpoint {directory!r} não retornou "
                            "logits válidos."
                        )

                    self._validate_logits(logits, len(texts))
                    logits_by_checkpoint.append(logits)

                ensemble_logits = torch.stack(
                    logits_by_checkpoint,
                    dim=0,
                ).mean(dim=0)
                self._validate_logits(ensemble_logits, len(texts))
                probabilities = torch.softmax(
                    ensemble_logits,
                    dim=-1,
                )
        except ModelPredictionError:
            raise
        except Exception as error:
            raise ModelPredictionError(
                f"Falha durante a inferência do ensemble: {error}"
            ) from error

        self._synchronize_cuda()

        ensemble_logits_cpu = ensemble_logits.detach().to(
            dtype=torch.float32,
            device="cpu",
        )
        probabilities_cpu = probabilities.detach().to(
            dtype=torch.float32,
            device="cpu",
        )
        checkpoint_logits_cpu = [
            logits.detach().to(dtype=torch.float32, device="cpu")
            for logits in logits_by_checkpoint
        ]

        positive_index = self._require_class_index(
            self.positive_index,
            "POSITIVE",
        )
        negative_index = self._require_class_index(
            self.negative_index,
            "NEGATIVE",
        )
        neutral_index = self._require_class_index(
            self.neutral_index,
            "NEUTRAL",
        )
        predictions: list[ModelPrediction] = []

        for row_index in range(probabilities_cpu.shape[0]):
            probability_row = probabilities_cpu[row_index]
            predicted_class_index = int(
                torch.argmax(probability_row).item()
            )
            predicted_label = self.id2label.get(predicted_class_index)

            if predicted_label is None:
                raise ModelPredictionError(
                    "O índice previsto não possui rótulo: "
                    f"{predicted_class_index}."
                )

            predictions.append(
                ModelPrediction(
                    predicted_label=predicted_label,
                    confidence=float(
                        probability_row[predicted_class_index].item()
                    ),
                    prob_positive=float(
                        probability_row[positive_index].item()
                    ),
                    prob_negative=float(
                        probability_row[negative_index].item()
                    ),
                    prob_neutral=float(
                        probability_row[neutral_index].item()
                    ),
                    extra={
                        "predicted_class_index": predicted_class_index,
                        "original_model_label": predicted_label,
                        "token_count": token_counts[row_index],
                        "ensemble_method": "mean_raw_logits",
                        "ensemble_size": len(self.models),
                        "checkpoint_directories": list(
                            self.checkpoint_directories
                        ),
                        "ensemble_logits": [
                            float(value)
                            for value in ensemble_logits_cpu[
                                row_index
                            ].tolist()
                        ],
                        "checkpoint_logits": {
                            directory: [
                                float(value)
                                for value in checkpoint_logits_cpu[
                                    checkpoint_index
                                ][row_index].tolist()
                            ]
                            for checkpoint_index, directory in enumerate(
                                self.checkpoint_directories
                            )
                        },
                        "probability_function": "softmax",
                        "score_normalization": "none",
                    },
                )
            )

        return predictions

    def _release_resources(self) -> None:
        """Remove referências aos três modelos e ao tokenizer."""

        self.models.clear()
        self.model = None
        self.tokenizer = None

    def get_metadata(self) -> dict[str, Any]:
        """Retorna metadados científicos e de runtime do ensemble."""

        metadata = BaseSentimentModel.get_metadata(self)
        configured_model_key = None

        if self.model_configuration is not None:
            configured_model_key = getattr(
                self.model_configuration,
                "key",
                None,
            )

        metadata.update(
            {
                "configured_model_key": configured_model_key,
                "model_family": "BERT",
                "base_model": "lucas-leme/FinBERT-PT-BR",
                "model_domain": "financial",
                "model_language": "pt-BR",
                "task": "sentiment_classification",
                "ensemble": True,
                "ensemble_method": "mean_raw_logits",
                "ensemble_size": len(self.checkpoint_directories),
                "checkpoint_directories": list(
                    self.checkpoint_directories
                ),
                "checkpoint_architectures": dict(
                    self.checkpoint_architectures
                ),
                "checkpoint_problem_types": dict(
                    self.checkpoint_problem_types
                ),
                "configured_probability_function": "softmax",
                "resolved_probability_function": "softmax",
                "score_normalization": "none",
                "continuous_sentiment_formula": (
                    "prob_positive - prob_negative"
                ),
                "model_max_length": self.model_max_length,
                "id2label": dict(self.id2label),
                "class_indices": {
                    "positive": self.positive_index,
                    "negative": self.negative_index,
                    "neutral": self.neutral_index,
                },
                "transformers_runtime_version": transformers.__version__,
                "local_files_only": self.local_files_only,
                "trust_remote_code": self.trust_remote_code,
                "use_fast_tokenizer": self.use_fast_tokenizer,
                "use_safetensors": True,
                "validate_identical_tokenizers": (
                    self.validate_identical_tokenizers
                ),
                "reject_git_lfs_pointers": self.reject_git_lfs_pointers,
                "detected_weight_files": list(
                    self.detected_weight_files
                ),
                "detected_tokenizer_files": list(
                    self.detected_tokenizer_files
                ),
                "loading_configuration": dict(
                    self.loading_configuration
                ),
                "validation_configuration": dict(
                    self.validation_configuration
                ),
            }
        )

        return metadata


__all__ = [
    "DEFAULT_CHECKPOINT_DIRECTORIES",
    "DEFAULT_MODEL_NAME",
    "PtBrFinancialSentimentAnalysisModel",
]
