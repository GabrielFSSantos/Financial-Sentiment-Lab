"""Adaptador compartilhado para checkpoints FinBERT locais (Hugging Face)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import torch
import transformers
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BertForSequenceClassification,
    BertTokenizer,
)

from modules.models.base import (
    BaseSentimentModel,
    ModelConfigurationError,
    ModelLoadingError,
    ModelPrediction,
    ModelPredictionError,
)

if TYPE_CHECKING:
    from modules.models.config.loader import ModelConfiguration


DEFAULT_MODEL_NAME = "finbert_hf"

EXPECTED_LABELS: frozenset[str] = frozenset(
    {
        "POSITIVE",
        "NEGATIVE",
        "NEUTRAL",
    }
)

SUPPORTED_PROBABILITY_FUNCTIONS: frozenset[str] = frozenset(
    {
        "softmax",
        "sigmoid",
        "model_config",
    }
)

SINGLE_WEIGHT_FILES: tuple[str, ...] = (
    "model.safetensors",
    "pytorch_model.bin",
)

SHARDED_WEIGHT_INDEX_FILES: tuple[str, ...] = (
    "model.safetensors.index.json",
    "pytorch_model.bin.index.json",
)

SUPPORTED_TOKENIZER_FILES: tuple[str, ...] = (
    "tokenizer.json",
    "vocab.txt",
    "spiece.model",
    "sentencepiece.bpe.model",
)


class FinBertHfModel(BaseSentimentModel):
    """Adaptador genérico para FinBERT (PT ou EN) em ``model_store/``."""

    def __init__(
        self,
        model_dir: str | Path,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = 32,
        max_length: int = 512,
        device: str = "auto",
        probability_function: str = "softmax",
        model_configuration: "ModelConfiguration | None" = None,
        loading: Mapping[str, Any] | None = None,
        validation: Mapping[str, Any] | None = None,
    ) -> None:
        """Inicializa o adaptador sem carregar os pesos."""

        super().__init__(
            model_name=model_name,
            model_dir=model_dir,
            batch_size=batch_size,
            max_length=max_length,
            device=device,
        )

        self.model_configuration = model_configuration
        self.loading_configuration = self._normalize_mapping(
            loading,
            "loading",
        )
        self.validation_configuration = self._normalize_mapping(
            validation,
            "validation",
        )

        normalized_probability_function = (
            str(probability_function).strip().lower()
        )

        if (
            normalized_probability_function
            not in SUPPORTED_PROBABILITY_FUNCTIONS
        ):
            raise ModelConfigurationError(
                "probability_function precisa ser softmax, sigmoid "
                "ou model_config. "
                f"Valor recebido: {probability_function!r}."
            )

        self.probability_function = (
            normalized_probability_function
        )
        self.resolved_probability_function: str | None = None
        self.score_normalization: str | None = None

        self.local_files_only = self._configuration_boolean(
            self.loading_configuration,
            "local_files_only",
            default=True,
        )
        self.trust_remote_code = self._configuration_boolean(
            self.loading_configuration,
            "trust_remote_code",
            default=False,
        )
        self.use_fast_tokenizer = self._configuration_boolean(
            self.loading_configuration,
            "use_fast_tokenizer",
            default=True,
        )
        self.use_safetensors = self._optional_boolean(
            self.loading_configuration.get("use_safetensors"),
            "loading.use_safetensors",
        )

        if not self.local_files_only:
            raise ModelConfigurationError(
                "FinBertHfModel exige local_files_only=true. "
                "Downloads devem ser realizados antes do experimento."
            )

        if self.trust_remote_code:
            raise ModelConfigurationError(
                "trust_remote_code=true não é permitido para este "
                "adaptador local."
            )

        self.strict_model_type = self._configuration_boolean(
            self.validation_configuration,
            "strict_model_type",
            default=True,
        )
        self.strict_architecture = self._configuration_boolean(
            self.validation_configuration,
            "strict_architecture",
            default=True,
        )
        self.validate_configured_labels = (
            self._configuration_boolean(
                self.validation_configuration,
                "validate_configured_labels",
                default=True,
            )
        )

        self.id2label: dict[int, str] = {}
        self.positive_index: int | None = None
        self.negative_index: int | None = None
        self.neutral_index: int | None = None

        self.model_config_data: dict[str, Any] = {}
        self.model_max_length: int | None = None
        self.original_problem_type: str | None = None
        self.loaded_problem_type: str | None = None
        self.detected_weight_files: tuple[str, ...] = tuple()
        self.detected_tokenizer_files: tuple[str, ...] = tuple()
        self.detected_shard_files: tuple[str, ...] = tuple()

    @staticmethod
    def _normalize_mapping(
        value: Mapping[str, Any] | None,
        field_name: str,
    ) -> dict[str, Any]:
        """Copia uma configuração opcional e valida seu tipo."""

        if value is None:
            return {}

        if not isinstance(value, Mapping):
            raise ModelConfigurationError(
                f"{field_name} precisa ser um mapeamento."
            )

        return dict(value)

    @staticmethod
    def _configuration_boolean(
        mapping: Mapping[str, Any],
        key: str,
        *,
        default: bool,
    ) -> bool:
        """Obtém um booleano de uma configuração."""

        if key not in mapping:
            return default

        value = mapping[key]
        normalized = FinBertHfModel._optional_boolean(
            value,
            key,
        )

        if normalized is None:
            raise ModelConfigurationError(
                f"{key} não pode ser nulo."
            )

        return normalized

    @staticmethod
    def _optional_boolean(
        value: Any,
        field_name: str,
    ) -> bool | None:
        """Normaliza booleanos opcionais sem usar ``bool(string)``."""

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, int) and value in {0, 1}:
            return bool(value)

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {
                "1",
                "true",
                "yes",
                "y",
                "on",
                "sim",
                "s",
            }:
                return True

            if normalized in {
                "0",
                "false",
                "no",
                "n",
                "off",
                "nao",
                "não",
            }:
                return False

        raise ModelConfigurationError(
            f"{field_name} precisa ser booleano. "
            f"Valor recebido: {value!r}."
        )

    def validate_model_files(self) -> None:
        """Valida config, pesos, shards e arquivos do tokenizer."""

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Pasta do modelo {self.model_name!r} não encontrada: "
                f"{self.model_dir}"
            )

        if not self.model_dir.is_dir():
            raise NotADirectoryError(
                f"O caminho configurado para o modelo "
                f"{self.model_name!r} não é uma pasta: {self.model_dir}"
            )

        config_path = self.model_dir / "config.json"

        if not config_path.is_file():
            raise FileNotFoundError(
                "Arquivo config.json não encontrado em: "
                f"{self.model_dir}"
            )

        weight_files, shard_files = self._validate_weight_files()
        tokenizer_files = tuple(
            filename
            for filename in SUPPORTED_TOKENIZER_FILES
            if (self.model_dir / filename).is_file()
        )

        if not tokenizer_files:
            raise FileNotFoundError(
                "Nenhum arquivo principal do tokenizer foi encontrado "
                f"em {self.model_dir}. Arquivos aceitos: "
                f"{', '.join(SUPPORTED_TOKENIZER_FILES)}."
            )

        config_data = self._read_json_object(
            config_path,
            description="config.json",
        )
        self._validate_config_data(config_data)

        self.model_config_data = config_data
        self.detected_weight_files = weight_files
        self.detected_shard_files = shard_files
        self.detected_tokenizer_files = tokenizer_files

    def _validate_weight_files(
        self,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Valida pesos únicos ou todos os shards declarados no índice."""

        single_files = tuple(
            filename
            for filename in SINGLE_WEIGHT_FILES
            if (self.model_dir / filename).is_file()
        )
        index_files = tuple(
            filename
            for filename in SHARDED_WEIGHT_INDEX_FILES
            if (self.model_dir / filename).is_file()
        )

        if self.use_safetensors is True:
            accepted_single = tuple(
                item
                for item in single_files
                if item.endswith(".safetensors")
            )
            accepted_indexes = tuple(
                item
                for item in index_files
                if item.startswith("model.safetensors")
            )
        elif self.use_safetensors is False:
            accepted_single = tuple(
                item
                for item in single_files
                if item.endswith(".bin")
            )
            accepted_indexes = tuple(
                item
                for item in index_files
                if item.startswith("pytorch_model.bin")
            )
        else:
            accepted_single = single_files
            accepted_indexes = index_files

        if not accepted_single and not accepted_indexes:
            requested_format = (
                "safetensors"
                if self.use_safetensors is True
                else "PyTorch bin"
                if self.use_safetensors is False
                else "safetensors ou PyTorch bin"
            )
            raise FileNotFoundError(
                "Nenhum conjunto de pesos compatível foi encontrado "
                f"em {self.model_dir}. Formato solicitado: "
                f"{requested_format}."
            )

        shard_names: set[str] = set()

        for index_filename in accepted_indexes:
            index_path = self.model_dir / index_filename
            index_data = self._read_json_object(
                index_path,
                description=index_filename,
            )
            weight_map = index_data.get("weight_map")

            if not isinstance(weight_map, Mapping):
                raise ModelConfigurationError(
                    f"{index_filename} não possui weight_map válido."
                )

            for raw_shard_name in weight_map.values():
                shard_name = str(raw_shard_name).strip()
                shard_path = Path(shard_name)

                if (
                    not shard_name
                    or shard_path.is_absolute()
                    or ".." in shard_path.parts
                ):
                    raise ModelConfigurationError(
                        f"Shard inválido em {index_filename}: "
                        f"{raw_shard_name!r}."
                    )

                shard_names.add(shard_name)

        missing_shards = sorted(
            shard_name
            for shard_name in shard_names
            if not (self.model_dir / shard_name).is_file()
        )

        if missing_shards:
            formatted = "\n".join(
                f"  - {self.model_dir / shard_name}"
                for shard_name in missing_shards
            )
            raise FileNotFoundError(
                "O índice de pesos referencia shards ausentes:\n"
                f"{formatted}"
            )

        return (
            tuple(sorted({*accepted_single, *accepted_indexes})),
            tuple(sorted(shard_names)),
        )

    @staticmethod
    def _read_json_object(
        path: Path,
        *,
        description: str,
    ) -> dict[str, Any]:
        """Lê um arquivo JSON cujo conteúdo precisa ser um objeto."""

        try:
            with path.open("r", encoding="utf-8") as file:
                raw_data: Any = json.load(file)
        except json.JSONDecodeError as error:
            raise ModelConfigurationError(
                f"{description} possui JSON inválido: {error}"
            ) from error
        except OSError as error:
            raise ModelConfigurationError(
                f"Não foi possível ler {description}: {error}"
            ) from error

        if not isinstance(raw_data, dict):
            raise ModelConfigurationError(
                f"{description} precisa conter um objeto JSON."
            )

        return dict(raw_data)

    def _validate_config_data(
        self,
        config_data: Mapping[str, Any],
    ) -> None:
        """Valida arquitetura, classes e limite de posições."""

        model_type_value = config_data.get("model_type")
        model_type = (
            str(model_type_value).strip().lower()
            if model_type_value is not None
            else ""
        )

        if (
            self.strict_model_type
            and model_type
            and model_type != "bert"
        ):
            raise ModelConfigurationError(
                "O modelo informado não está configurado como BERT. "
                f"model_type encontrado: {model_type!r}."
            )

        architectures_value = config_data.get(
            "architectures",
            [],
        )

        if architectures_value is None:
            architectures_value = []

        if not isinstance(architectures_value, list):
            raise ModelConfigurationError(
                "O campo architectures precisa ser uma lista."
            )

        architecture_names = {
            str(architecture).strip()
            for architecture in architectures_value
            if str(architecture).strip()
        }

        if (
            self.strict_architecture
            and architecture_names
            and "BertForSequenceClassification"
            not in architecture_names
        ):
            raise ModelConfigurationError(
                "O modelo precisa utilizar "
                "BertForSequenceClassification. Arquiteturas "
                f"encontradas: {sorted(architecture_names)}."
            )

        id2label_value = config_data.get("id2label")

        if not isinstance(id2label_value, Mapping):
            raise ModelConfigurationError(
                "O config.json não possui id2label válido."
            )

        self._configure_class_indices(
            id2label_value,
            source="config.json",
        )
        self._validate_labels_against_models_yaml()

        max_positions_value = config_data.get(
            "max_position_embeddings"
        )
        self.model_max_length = self._parse_positive_integer(
            max_positions_value,
            "max_position_embeddings",
        )

        if self.max_length > self.model_max_length:
            raise ModelConfigurationError(
                f"O modelo aceita no máximo {self.model_max_length} "
                f"tokens, mas max_length recebeu {self.max_length}."
            )

        problem_type_value = config_data.get("problem_type")
        self.original_problem_type = (
            str(problem_type_value).strip()
            if problem_type_value is not None
            else None
        )
        self.resolved_probability_function = (
            self._resolve_probability_function(
                self.original_problem_type,
            )
        )
        self.score_normalization = (
            "l1_after_sigmoid"
            if self.resolved_probability_function == "sigmoid"
            else "none"
        )

    def _configure_class_indices(
        self,
        raw_id2label: Mapping[Any, Any],
        *,
        source: str,
    ) -> None:
        """Normaliza o mapeamento índice → classe."""

        normalized_labels: dict[int, str] = {}

        for raw_index, raw_label in raw_id2label.items():
            class_index = self._parse_non_negative_integer(
                raw_index,
                f"{source}.id2label.index",
            )
            class_label = str(raw_label).strip().upper()

            if not class_label:
                raise ModelConfigurationError(
                    f"Foi encontrado rótulo vazio em {source}.id2label."
                )

            if class_index in normalized_labels:
                raise ModelConfigurationError(
                    "Foi encontrado índice duplicado em "
                    f"{source}.id2label: {class_index}."
                )

            normalized_labels[class_index] = class_label

        if set(normalized_labels.values()) != EXPECTED_LABELS:
            raise ModelConfigurationError(
                f"O modelo {self.model_name!r} precisa possuir "
                "exatamente as classes POSITIVE, NEGATIVE e NEUTRAL. "
                f"Mapeamento encontrado em {source}: "
                f"{normalized_labels}."
            )

        if len(normalized_labels) != 3:
            raise ModelConfigurationError(
                "Esta implementação exige exatamente três classes."
            )

        label2id = {
            label: index
            for index, label in normalized_labels.items()
        }

        self.id2label = dict(
            sorted(normalized_labels.items())
        )
        self.positive_index = label2id["POSITIVE"]
        self.negative_index = label2id["NEGATIVE"]
        self.neutral_index = label2id["NEUTRAL"]

    def _validate_labels_against_models_yaml(self) -> None:
        """Compara config.json e ``models.yaml`` quando disponível."""

        if (
            not self.validate_configured_labels
            or self.model_configuration is None
        ):
            return

        labels = getattr(
            self.model_configuration,
            "labels",
            None,
        )

        if not isinstance(labels, Mapping):
            raise ModelConfigurationError(
                "model_configuration.labels precisa ser um mapeamento."
            )

        configured_id2label = labels.get("id2label")

        if not isinstance(configured_id2label, Mapping):
            raise ModelConfigurationError(
                "models.yaml não possui labels.id2label válido."
            )

        normalized_configured: dict[int, str] = {}

        for raw_index, raw_label in configured_id2label.items():
            index_value = self._parse_non_negative_integer(
                raw_index,
                "models.yaml.labels.id2label.index",
            )
            normalized_configured[index_value] = (
                str(raw_label).strip().upper()
            )

        if normalized_configured != self.id2label:
            raise ModelConfigurationError(
                "O mapeamento de classes de models.yaml diverge do "
                "config.json do modelo. "
                f"models.yaml={normalized_configured}; "
                f"config.json={self.id2label}."
            )

    def _resolve_probability_function(
        self,
        problem_type: str | None,
    ) -> str:
        """Resolve a função efetiva sem alterar o config do modelo."""

        if self.probability_function != "model_config":
            return self.probability_function

        normalized_problem_type = (
            str(problem_type).strip().lower()
            if problem_type is not None
            else ""
        )

        if normalized_problem_type == "multi_label_classification":
            return "sigmoid"

        return "softmax"

    def _get_model_config_data(self) -> dict[str, Any]:
        """Retorna config.json em memória ou lê do disco."""

        if self.model_config_data:
            return self.model_config_data

        config_path = self.model_dir / "config.json"
        if not config_path.is_file():
            return {}

        return self._read_json_object(
            config_path,
            description="config.json",
        )

    def _uses_legacy_bert_config(self) -> bool:
        """Checkpoints antigos sem model_type no config.json."""

        config_data = self._get_model_config_data()
        model_type = config_data.get("model_type")
        if model_type is not None and str(model_type).strip():
            return False

        architectures = config_data.get("architectures") or []
        architecture_names = {
            str(name).strip()
            for name in architectures
            if str(name).strip()
        }
        return "BertForSequenceClassification" in architecture_names

    def _load_model(self) -> None:
        """Carrega tokenizer e pesos usando somente arquivos locais."""

        tokenizer_arguments: dict[str, Any] = {
            "local_files_only": self.local_files_only,
            "trust_remote_code": self.trust_remote_code,
            "use_fast": self.use_fast_tokenizer,
        }
        model_arguments: dict[str, Any] = {
            "local_files_only": self.local_files_only,
            "trust_remote_code": self.trust_remote_code,
        }

        if self.use_safetensors is not None:
            model_arguments["use_safetensors"] = (
                self.use_safetensors
            )

        try:
            if self._uses_legacy_bert_config():
                tokenizer = BertTokenizer.from_pretrained(
                    str(self.model_dir),
                    local_files_only=self.local_files_only,
                )
                model = BertForSequenceClassification.from_pretrained(
                    str(self.model_dir),
                    **model_arguments,
                )
            else:
                tokenizer = AutoTokenizer.from_pretrained(
                    str(self.model_dir),
                    **tokenizer_arguments,
                )
                model = (
                    AutoModelForSequenceClassification.from_pretrained(
                        str(self.model_dir),
                        **model_arguments,
                    )
                )
        except Exception as error:
            raise ModelLoadingError(
                "Falha ao carregar os arquivos locais do modelo "
                f"{self.model_name!r} em {self.model_dir}: {error}"
            ) from error

        loaded_id2label_value = getattr(
            model.config,
            "id2label",
            None,
        )

        if not isinstance(loaded_id2label_value, Mapping):
            raise ModelLoadingError(
                "O modelo carregado não possui id2label válido."
            )

        self._configure_class_indices(
            loaded_id2label_value,
            source="model.config",
        )
        self._validate_labels_against_models_yaml()

        loaded_max_length = self._parse_positive_integer(
            getattr(
                model.config,
                "max_position_embeddings",
                None,
            ),
            "model.config.max_position_embeddings",
        )
        self.model_max_length = loaded_max_length

        if self.max_length > loaded_max_length:
            raise ModelLoadingError(
                f"O modelo carregado aceita no máximo "
                f"{loaded_max_length} tokens, mas max_length recebeu "
                f"{self.max_length}."
            )

        loaded_problem_type_value = getattr(
            model.config,
            "problem_type",
            None,
        )
        self.loaded_problem_type = (
            str(loaded_problem_type_value).strip()
            if loaded_problem_type_value is not None
            else None
        )
        self.resolved_probability_function = (
            self._resolve_probability_function(
                self.loaded_problem_type,
            )
        )
        self.score_normalization = (
            "l1_after_sigmoid"
            if self.resolved_probability_function == "sigmoid"
            else "none"
        )

        try:
            model.to(self.device)
            model.eval()
        except Exception as error:
            raise ModelLoadingError(
                "Não foi possível mover o modelo "
                f"{self.model_name!r} para {self.device}: {error}"
            ) from error

        self.tokenizer = tokenizer
        self.model = model
        self._architecture_name = model.__class__.__name__

    def _predict_batch(
        self,
        texts: Sequence[str],
    ) -> list[ModelPrediction]:
        """Executa inferência de um lote e preserva a ordem."""

        if self.model is None:
            raise ModelPredictionError(
                "O modelo ainda não foi carregado."
            )

        if self.tokenizer is None:
            raise ModelPredictionError(
                "O tokenizer ainda não foi carregado."
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

        attention_mask_value = encoded_inputs.get(
            "attention_mask"
        )
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

            model_inputs[str(input_name)] = input_value.to(
                self.device
            )

        self._synchronize_cuda()

        try:
            with torch.inference_mode():
                outputs = self.model(**model_inputs)
                logits_value = getattr(
                    outputs,
                    "logits",
                    None,
                )

                if not isinstance(
                    logits_value,
                    torch.Tensor,
                ):
                    raise ModelPredictionError(
                        "O modelo não retornou logits válidos."
                    )

                logits = logits_value
                self._validate_logits(
                    logits,
                    len(texts),
                )
                raw_scores, probabilities = (
                    self._scores_from_logits(logits)
                )
        except ModelPredictionError:
            raise
        except Exception as error:
            raise ModelPredictionError(
                f"Falha durante a inferência: {error}"
            ) from error

        self._synchronize_cuda()

        logits_cpu = logits.detach().to(
            dtype=torch.float32,
            device="cpu",
        )
        raw_scores_cpu = raw_scores.detach().to(
            dtype=torch.float32,
            device="cpu",
        )
        probabilities_cpu = probabilities.detach().to(
            dtype=torch.float32,
            device="cpu",
        )

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
            raw_score_row = raw_scores_cpu[row_index]
            predicted_class_index = int(
                torch.argmax(probability_row).item()
            )
            predicted_label = self.id2label.get(
                predicted_class_index
            )

            if predicted_label is None:
                raise ModelPredictionError(
                    "O índice previsto não possui rótulo: "
                    f"{predicted_class_index}."
                )

            raw_class_scores = {
                self.id2label[class_index]: float(
                    raw_score_row[class_index].item()
                )
                for class_index in sorted(self.id2label)
            }

            prediction = ModelPrediction(
                predicted_label=predicted_label,
                confidence=float(
                    probability_row[
                        predicted_class_index
                    ].item()
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
                continuous_sentiment=None,
                processing_time_ms=None,
                extra={
                    "predicted_class_index": (
                        predicted_class_index
                    ),
                    "original_model_label": predicted_label,
                    "token_count": token_counts[row_index],
                    "logits": [
                        float(value)
                        for value in logits_cpu[
                            row_index
                        ].tolist()
                    ],
                    "raw_class_scores": raw_class_scores,
                    "raw_score_sum": float(
                        raw_score_row.sum().item()
                    ),
                    "probability_function": (
                        self.resolved_probability_function
                    ),
                    "score_normalization": (
                        self.score_normalization
                    ),
                },
            )
            predictions.append(prediction)

        return predictions

    def _scores_from_logits(
        self,
        logits: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Calcula escores brutos e probabilidades padronizadas."""

        probability_function = (
            self.resolved_probability_function
            or self._resolve_probability_function(
                self.loaded_problem_type
                or self.original_problem_type
            )
        )

        if probability_function == "softmax":
            raw_scores = torch.softmax(logits, dim=-1)
            probabilities = raw_scores
        elif probability_function == "sigmoid":
            raw_scores = torch.sigmoid(logits)
            score_sums = raw_scores.sum(
                dim=-1,
                keepdim=True,
            )

            if torch.any(score_sums <= 0):
                raise ModelPredictionError(
                    "Os escores sigmoid não puderam ser normalizados."
                )

            probabilities = raw_scores / score_sums
        else:
            raise ModelPredictionError(
                "Função de probabilidade não resolvida: "
                f"{probability_function!r}."
            )

        if not torch.all(torch.isfinite(raw_scores)):
            raise ModelPredictionError(
                "Os escores do modelo possuem NaN ou infinito."
            )

        if not torch.all(torch.isfinite(probabilities)):
            raise ModelPredictionError(
                "As probabilidades possuem NaN ou infinito."
            )

        probability_sums = probabilities.sum(dim=-1)

        if not torch.allclose(
            probability_sums,
            torch.ones_like(probability_sums),
            atol=1e-5,
            rtol=0.0,
        ):
            raise ModelPredictionError(
                "As probabilidades padronizadas não somam 1."
            )

        return raw_scores, probabilities

    def _validate_logits(
        self,
        logits: torch.Tensor,
        batch_size: int,
    ) -> None:
        """Valida dimensão, quantidade de linhas e classes."""

        if logits.ndim != 2:
            raise ModelPredictionError(
                "O modelo retornou logits em formato inesperado. "
                f"Shape: {tuple(logits.shape)}."
            )

        if logits.shape[0] != batch_size:
            raise ModelPredictionError(
                "A quantidade de linhas dos logits não corresponde "
                f"aos textos: {logits.shape[0]} != {batch_size}."
            )

        if logits.shape[1] != len(self.id2label):
            raise ModelPredictionError(
                "A quantidade de logits por texto não corresponde "
                f"às classes: {logits.shape[1]} != "
                f"{len(self.id2label)}."
            )

        if not torch.all(torch.isfinite(logits)):
            raise ModelPredictionError(
                "Os logits possuem NaN ou infinito."
            )

    @staticmethod
    def _extract_token_counts(
        attention_mask: torch.Tensor | None,
        batch_size: int,
    ) -> list[int | None]:
        """Extrai a quantidade de tokens válidos por texto."""

        if attention_mask is None:
            return [None for _ in range(batch_size)]

        if attention_mask.ndim != 2:
            raise ModelPredictionError(
                "attention_mask possui formato inválido: "
                f"{tuple(attention_mask.shape)}."
            )

        if attention_mask.shape[0] != batch_size:
            raise ModelPredictionError(
                "attention_mask não corresponde à quantidade de textos."
            )

        token_count_tensor = attention_mask.sum(
            dim=1
        ).detach().to(
            dtype=torch.int64,
            device="cpu",
        )

        return [
            int(value.item())
            for value in token_count_tensor
        ]

    def _synchronize_cuda(self) -> None:
        """Sincroniza somente quando o adaptador está em CUDA."""

        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

    @staticmethod
    def _require_class_index(
        class_index: int | None,
        class_name: str,
    ) -> int:
        """Garante que uma classe tenha índice configurado."""

        if class_index is None:
            raise ModelPredictionError(
                f"O índice da classe {class_name} não foi configurado."
            )

        return class_index

    @staticmethod
    def _parse_positive_integer(
        value: Any,
        field_name: str,
    ) -> int:
        """Converte um inteiro obrigatório maior que zero."""

        normalized_value = FinBertHfModel._parse_integer(
            value,
            field_name,
        )

        if normalized_value <= 0:
            raise ModelConfigurationError(
                f"{field_name} precisa ser maior que zero."
            )

        return normalized_value

    @staticmethod
    def _parse_non_negative_integer(
        value: Any,
        field_name: str,
    ) -> int:
        """Converte um inteiro obrigatório maior ou igual a zero."""

        normalized_value = FinBertHfModel._parse_integer(
            value,
            field_name,
        )

        if normalized_value < 0:
            raise ModelConfigurationError(
                f"{field_name} não pode ser negativo."
            )

        return normalized_value

    @staticmethod
    def _parse_integer(
        value: Any,
        field_name: str,
    ) -> int:
        """Converte inteiros sem aceitar booleanos ou frações."""

        if value is None:
            raise ModelConfigurationError(
                f"{field_name} não foi encontrado."
            )

        if isinstance(value, bool):
            raise ModelConfigurationError(
                f"{field_name} precisa ser inteiro."
            )

        if isinstance(value, int):
            return value

        if isinstance(value, str):
            stripped = value.strip()

            try:
                return int(stripped, 10)
            except ValueError as error:
                raise ModelConfigurationError(
                    f"{field_name} precisa ser inteiro. "
                    f"Valor: {value!r}."
                ) from error

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as error:
            raise ModelConfigurationError(
                f"{field_name} precisa ser inteiro. "
                f"Valor: {value!r}."
            ) from error

        if (
            not math.isfinite(numeric_value)
            or not numeric_value.is_integer()
        ):
            raise ModelConfigurationError(
                f"{field_name} precisa ser inteiro. "
                f"Valor: {value!r}."
            )

        return int(numeric_value)

    def _release_resources(self) -> None:
        """Remove referências ao modelo e ao tokenizer."""

        self.model = None
        self.tokenizer = None

    def get_metadata(self) -> dict[str, Any]:
        """Retorna metadados gerais e específicos do checkpoint FinBERT."""

        metadata = super().get_metadata()

        tokenizer_class: str | None = None
        runtime_problem_type: str | None = None
        config_transformers_version: str | None = None

        if self.tokenizer is not None:
            tokenizer_class = self.tokenizer.__class__.__name__

        if self.model is not None:
            problem_type_value = getattr(
                self.model.config,
                "problem_type",
                None,
            )
            runtime_problem_type = (
                str(problem_type_value)
                if problem_type_value is not None
                else None
            )

        configured_transformers_version = (
            self.model_config_data.get(
                "transformers_version"
            )
        )

        if configured_transformers_version is not None:
            config_transformers_version = str(
                configured_transformers_version
            )

        configured_model_key = None
        model_language: str | None = None

        if self.model_configuration is not None:
            configured_model_key = getattr(
                self.model_configuration,
                "key",
                None,
            )
            configured_language = self.model_configuration.metadata.get(
                "language"
            )
            if configured_language is not None:
                model_language = str(configured_language)
            else:
                model_language = self.model_configuration.language

        metadata.update(
            {
                "configured_model_key": configured_model_key,
                "model_family": "BERT",
                "model_domain": "financial",
                "model_language": model_language,
                "task": "sentiment_classification",
                "configured_probability_function": (
                    self.probability_function
                ),
                "resolved_probability_function": (
                    self.resolved_probability_function
                ),
                "score_normalization": self.score_normalization,
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
                "original_problem_type": (
                    self.original_problem_type
                ),
                "loaded_problem_type": self.loaded_problem_type,
                "runtime_problem_type": runtime_problem_type,
                "transformers_runtime_version": (
                    transformers.__version__
                ),
                "transformers_config_version": (
                    config_transformers_version
                ),
                "tokenizer_class": tokenizer_class,
                "local_files_only": self.local_files_only,
                "trust_remote_code": self.trust_remote_code,
                "use_fast_tokenizer": self.use_fast_tokenizer,
                "use_safetensors": self.use_safetensors,
                "detected_weight_files": list(
                    self.detected_weight_files
                ),
                "detected_weight_shards": list(
                    self.detected_shard_files
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
    "DEFAULT_MODEL_NAME",
    "EXPECTED_LABELS",
    "FinBertHfModel",
    "SUPPORTED_PROBABILITY_FUNCTIONS",
]
