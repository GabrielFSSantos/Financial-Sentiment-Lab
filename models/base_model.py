#!/usr/bin/env python3

"""Contrato comum dos modelos de análise de sentimentos.

Cada adaptador específico deve herdar :class:`BaseSentimentModel` e
implementar:

- ``validate_model_files()``;
- ``_load_model()``;
- ``_predict_batch()``.

A classe-base centraliza validação, resolução de dispositivo, execução em
lotes, medição de tempo, liberação de memória e metadados. Todos os
adaptadores devolvem objetos :class:`ModelPrediction`, permitindo que a
pipeline trate modelos diferentes de maneira uniforme.
"""

from __future__ import annotations

import gc
import math
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from operator import index as integer_index
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence

import torch

from pipeline.output_schema import (
    calculate_continuous_sentiment,
    normalize_sentiment_label,
)


CANONICAL_SENTIMENT_LABELS: tuple[str, ...] = (
    "NEGATIVE",
    "NEUTRAL",
    "POSITIVE",
)


class ModelConfigurationError(ValueError):
    """Indica configuração inválida do adaptador ou do modelo."""


class ModelLoadingError(RuntimeError):
    """Indica falha ao carregar tokenizer ou pesos."""


class ModelPredictionError(RuntimeError):
    """Indica falha ou saída inválida durante a inferência."""


@dataclass
class ModelPrediction:
    """Previsão padronizada produzida para um único texto.

    Campos de identificação do dataset, como ``run_id``, ``news_id``,
    ``company`` e ``date``, são adicionados posteriormente pelo runner.

    ``extra`` permanece aninhado para que ``pipeline.output_schema`` possa
    serializá-lo no campo de metadados sem misturar informações específicas
    do adaptador com o contrato principal.
    """

    predicted_label: str
    confidence: float | None = None
    prob_positive: float | None = None
    prob_negative: float | None = None
    prob_neutral: float | None = None
    continuous_sentiment: float | None = None
    processing_time_ms: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normaliza e valida todos os campos da previsão."""

        try:
            normalized_label = normalize_sentiment_label(
                self.predicted_label
            )
        except ValueError as error:
            raise ModelPredictionError(str(error)) from error

        if normalized_label is None:
            raise ModelPredictionError(
                "A previsão precisa possuir uma classe de sentimento."
            )

        self.predicted_label = normalized_label

        self.confidence = self._normalize_probability(
            self.confidence,
            "confidence",
        )
        self.prob_positive = self._normalize_probability(
            self.prob_positive,
            "prob_positive",
        )
        self.prob_negative = self._normalize_probability(
            self.prob_negative,
            "prob_negative",
        )
        self.prob_neutral = self._normalize_probability(
            self.prob_neutral,
            "prob_neutral",
        )

        probability_by_label = {
            "POSITIVE": self.prob_positive,
            "NEGATIVE": self.prob_negative,
            "NEUTRAL": self.prob_neutral,
        }
        available_probabilities = [
            probability
            for probability in probability_by_label.values()
            if probability is not None
        ]

        if len(available_probabilities) == 3:
            probability_sum = float(sum(available_probabilities))

            if not math.isclose(
                probability_sum,
                1.0,
                abs_tol=0.02,
                rel_tol=0.0,
            ):
                raise ModelPredictionError(
                    "As probabilidades positiva, negativa e neutra "
                    "devem somar aproximadamente 1. "
                    f"Soma recebida: {probability_sum:.8f}."
                )

            maximum_probability = max(available_probabilities)
            predicted_probability = probability_by_label[
                self.predicted_label
            ]

            if predicted_probability is None:
                raise ModelPredictionError(
                    "A classe prevista não possui probabilidade associada."
                )

            if (
                predicted_probability + 1e-7
                < maximum_probability
            ):
                raise ModelPredictionError(
                    "predicted_label não corresponde à maior "
                    "probabilidade fornecida."
                )

            if self.confidence is None:
                self.confidence = maximum_probability
            elif not math.isclose(
                self.confidence,
                maximum_probability,
                abs_tol=1e-6,
                rel_tol=0.0,
            ):
                raise ModelPredictionError(
                    "confidence precisa corresponder à maior "
                    "probabilidade da previsão."
                )

        calculated_sentiment = calculate_continuous_sentiment(
            prob_positive=self.prob_positive,
            prob_negative=self.prob_negative,
        )

        if self.continuous_sentiment is None:
            self.continuous_sentiment = calculated_sentiment
        else:
            normalized_sentiment = self._normalize_finite_float(
                self.continuous_sentiment,
                "continuous_sentiment",
            )

            if not -1.0 <= normalized_sentiment <= 1.0:
                raise ModelPredictionError(
                    "continuous_sentiment precisa estar entre -1 e 1."
                )

            if (
                calculated_sentiment is not None
                and not math.isclose(
                    normalized_sentiment,
                    calculated_sentiment,
                    abs_tol=1e-6,
                    rel_tol=0.0,
                )
            ):
                raise ModelPredictionError(
                    "continuous_sentiment não corresponde a "
                    "prob_positive - prob_negative."
                )

            self.continuous_sentiment = normalized_sentiment

        if self.processing_time_ms is not None:
            normalized_time = self._normalize_finite_float(
                self.processing_time_ms,
                "processing_time_ms",
            )

            if normalized_time < 0:
                raise ModelPredictionError(
                    "processing_time_ms não pode ser negativo."
                )

            self.processing_time_ms = normalized_time

        if not isinstance(self.extra, dict):
            raise ModelPredictionError(
                "O campo extra precisa ser um dicionário."
            )

        self.extra = dict(self.extra)

    @staticmethod
    def _normalize_probability(
        value: float | None,
        field_name: str,
    ) -> float | None:
        """Converte e valida uma probabilidade opcional."""

        if value is None:
            return None

        normalized_value = ModelPrediction._normalize_finite_float(
            value,
            field_name,
        )

        if not 0.0 <= normalized_value <= 1.0:
            raise ModelPredictionError(
                f"{field_name} precisa estar entre 0 e 1. "
                f"Valor recebido: {normalized_value}."
            )

        return normalized_value

    @staticmethod
    def _normalize_finite_float(
        value: Any,
        field_name: str,
    ) -> float:
        """Converte um valor numérico e exige resultado finito."""

        if isinstance(value, bool):
            raise ModelPredictionError(
                f"{field_name} precisa ser numérico, não booleano."
            )

        try:
            normalized_value = float(value)
        except (TypeError, ValueError) as error:
            raise ModelPredictionError(
                f"{field_name} precisa ser numérico."
            ) from error

        if not math.isfinite(normalized_value):
            raise ModelPredictionError(
                f"{field_name} precisa ser um número finito."
            )

        return normalized_value

    def to_dict(self) -> dict[str, Any]:
        """Converte a previsão preservando ``extra`` como subestrutura."""

        return asdict(self)


class BaseSentimentModel(ABC):
    """Classe abstrata comum aos modelos de sentimento."""

    VALID_DEVICES: frozenset[str] = frozenset(
        {
            "auto",
            "cpu",
            "cuda",
        }
    )

    def __init__(
        self,
        model_name: str,
        model_dir: str | Path,
        batch_size: int = 32,
        max_length: int = 512,
        device: str = "auto",
    ) -> None:
        """Inicializa as configurações comuns do adaptador."""

        normalized_name = str(model_name).strip()

        if not normalized_name:
            raise ModelConfigurationError(
                "model_name não pode ser vazio."
            )

        normalized_batch_size = self._normalize_positive_integer(
            value=batch_size,
            field_name="batch_size",
        )
        normalized_max_length = self._normalize_positive_integer(
            value=max_length,
            field_name="max_length",
        )
        normalized_device = str(device).strip().lower()

        if normalized_device not in self.VALID_DEVICES:
            raise ModelConfigurationError(
                "device precisa ser auto, cpu ou cuda. "
                f"Valor recebido: {device!r}."
            )

        self.model_name = normalized_name
        self.model_dir = Path(model_dir).expanduser().resolve()
        self.batch_size = normalized_batch_size
        self.max_length = normalized_max_length
        self.requested_device = normalized_device
        self.device = self._resolve_device(normalized_device)

        self.model: Any = None
        self.tokenizer: Any = None

        self._loaded = False
        self._load_time_seconds: float | None = None
        self._architecture_name: str | None = None

    @property
    def is_loaded(self) -> bool:
        """Informa se tokenizer e pesos estão carregados."""

        return self._loaded

    @property
    def device_type(self) -> str:
        """Retorna o tipo efetivamente utilizado: ``cpu`` ou ``cuda``."""

        return self.device.type

    @property
    def device_name(self) -> str:
        """Retorna uma descrição legível do dispositivo."""

        if self.device.type != "cuda":
            return "CPU"

        try:
            return str(torch.cuda.get_device_name(self.device))
        except Exception:
            return "CUDA"

    @property
    def architecture_name(self) -> str | None:
        """Nome da arquitetura carregada pelo adaptador."""

        return self._architecture_name

    @property
    def load_time_seconds(self) -> float | None:
        """Tempo gasto no último carregamento bem-sucedido."""

        return self._load_time_seconds

    @abstractmethod
    def validate_model_files(self) -> None:
        """Valida os arquivos locais exigidos pelo adaptador."""

        raise NotImplementedError

    @abstractmethod
    def _load_model(self) -> None:
        """Carrega tokenizer e pesos e preenche os atributos comuns."""

        raise NotImplementedError

    @abstractmethod
    def _predict_batch(
        self,
        texts: Sequence[str],
    ) -> list[ModelPrediction]:
        """Classifica um lote preservando a ordem dos textos."""

        raise NotImplementedError

    def _release_resources(self) -> None:
        """Remove referências específicas do modelo."""

        self.model = None
        self.tokenizer = None

    def load(self) -> None:
        """Valida e carrega o modelo somente uma vez."""

        if self._loaded:
            return

        self.validate_model_files()
        started_at = perf_counter()

        try:
            self._load_model()

            if self.model is None:
                raise ModelLoadingError(
                    "O adaptador terminou o carregamento sem definir "
                    "self.model."
                )

            if self.tokenizer is None:
                raise ModelLoadingError(
                    "O adaptador terminou o carregamento sem definir "
                    "self.tokenizer."
                )

            self._loaded = True
            self._load_time_seconds = perf_counter() - started_at

        except Exception as error:
            self._loaded = False
            self._architecture_name = None

            try:
                self._release_resources()
            except Exception:
                pass

            if isinstance(error, ModelLoadingError):
                raise

            raise ModelLoadingError(
                f"Não foi possível carregar o modelo "
                f"{self.model_name!r}: {error}"
            ) from error

    def predict(
        self,
        texts: Sequence[str],
    ) -> list[ModelPrediction]:
        """Classifica textos em lotes e devolve previsões padronizadas."""

        normalized_texts = self._validate_texts(texts)

        if not normalized_texts:
            return []

        if not self._loaded:
            self.load()

        predictions: list[ModelPrediction] = []

        for batch_start in range(
            0,
            len(normalized_texts),
            self.batch_size,
        ):
            batch_end = min(
                batch_start + self.batch_size,
                len(normalized_texts),
            )
            batch_texts = normalized_texts[
                batch_start:batch_end
            ]

            started_at = perf_counter()

            try:
                batch_predictions = list(
                    self._predict_batch(batch_texts)
                )
            except ModelPredictionError as error:
                raise ModelPredictionError(
                    f"Erro no modelo {self.model_name!r}, lote "
                    f"{batch_start}:{batch_end}: {error}"
                ) from error
            except Exception as error:
                raise ModelPredictionError(
                    f"Erro inesperado no modelo {self.model_name!r}, "
                    f"lote {batch_start}:{batch_end}: {error}"
                ) from error

            elapsed_seconds = perf_counter() - started_at

            if len(batch_predictions) != len(batch_texts):
                raise ModelPredictionError(
                    f"O modelo {self.model_name!r} recebeu "
                    f"{len(batch_texts)} textos, mas retornou "
                    f"{len(batch_predictions)} previsões."
                )

            average_time_ms = (
                elapsed_seconds
                * 1000.0
                / len(batch_texts)
            )

            for prediction_index, prediction in enumerate(
                batch_predictions
            ):
                if not isinstance(
                    prediction,
                    ModelPrediction,
                ):
                    raise ModelPredictionError(
                        "A previsão de índice "
                        f"{batch_start + prediction_index} não é uma "
                        "instância de ModelPrediction."
                    )

                if prediction.processing_time_ms is None:
                    prediction.processing_time_ms = average_time_ms

                predictions.append(prediction)

        return predictions

    def unload(self) -> None:
        """Libera os recursos, inclusive o cache CUDA quando aplicável."""

        try:
            self._release_resources()
        finally:
            self._loaded = False
            self._architecture_name = None

            gc.collect()

            if (
                self.device.type == "cuda"
                and torch.cuda.is_available()
            ):
                torch.cuda.empty_cache()

    def get_metadata(self) -> dict[str, Any]:
        """Retorna configuração e informações do runtime do modelo."""

        metadata: dict[str, Any] = {
            "model_name": self.model_name,
            "adapter_class": self.__class__.__name__,
            "model_dir": str(self.model_dir),
            "architecture": self.architecture_name,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "requested_device": self.requested_device,
            "resolved_device": self.device_type,
            "device_name": self.device_name,
            "is_loaded": self.is_loaded,
            "load_time_seconds": self.load_time_seconds,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda,
        }

        if (
            self.device.type == "cuda"
            and torch.cuda.is_available()
        ):
            properties = torch.cuda.get_device_properties(
                self.device
            )
            metadata["gpu_count"] = torch.cuda.device_count()
            metadata["gpu_total_memory_mb"] = round(
                float(properties.total_memory)
                / 1024.0
                / 1024.0,
                2,
            )
        else:
            metadata["gpu_count"] = 0
            metadata["gpu_total_memory_mb"] = None

        return metadata

    def __enter__(self) -> "BaseSentimentModel":
        """Carrega o modelo ao entrar em um bloco ``with``."""

        self.load()
        return self

    def __exit__(
        self,
        exception_type: Any,
        exception_value: Any,
        traceback: Any,
    ) -> None:
        """Libera o modelo ao sair de um bloco ``with``."""

        del exception_type, exception_value, traceback
        self.unload()

    @staticmethod
    def _normalize_positive_integer(
        value: Any,
        field_name: str,
    ) -> int:
        """Converte estritamente um inteiro maior que zero.

        Valores fracionários como ``32.5`` são rejeitados em vez de serem
        truncados silenciosamente.
        """

        if isinstance(value, bool):
            raise ModelConfigurationError(
                f"{field_name} precisa ser um número inteiro."
            )

        normalized_value: int

        if isinstance(value, str):
            stripped = value.strip()

            if not stripped:
                raise ModelConfigurationError(
                    f"{field_name} precisa ser um número inteiro."
                )

            try:
                normalized_value = int(stripped, 10)
            except ValueError as error:
                raise ModelConfigurationError(
                    f"{field_name} precisa ser um número inteiro."
                ) from error
        else:
            try:
                normalized_value = int(integer_index(value))
            except (TypeError, ValueError, OverflowError) as error:
                raise ModelConfigurationError(
                    f"{field_name} precisa ser um número inteiro."
                ) from error

        if normalized_value <= 0:
            raise ModelConfigurationError(
                f"{field_name} precisa ser maior que zero."
            )

        return normalized_value

    @staticmethod
    def _validate_texts(
        texts: Sequence[str],
    ) -> list[str]:
        """Valida e remove espaços externos dos textos recebidos."""

        if isinstance(texts, (str, bytes)):
            raise ModelPredictionError(
                "texts precisa ser uma sequência de textos, "
                "e não uma única string."
            )

        normalized_texts: list[str] = []

        try:
            iterator = enumerate(texts)
        except TypeError as error:
            raise ModelPredictionError(
                "texts precisa ser uma sequência de textos."
            ) from error

        for item_index, text in iterator:
            if text is None:
                raise ModelPredictionError(
                    f"O texto de índice {item_index} é nulo."
                )

            normalized_text = str(text).strip()

            if not normalized_text:
                raise ModelPredictionError(
                    f"O texto de índice {item_index} está vazio."
                )

            normalized_texts.append(normalized_text)

        return normalized_texts

    @staticmethod
    def _resolve_device(
        requested_device: str,
    ) -> torch.device:
        """Resolve ``auto``, ``cpu`` ou ``cuda`` para um dispositivo."""

        if requested_device == "cpu":
            return torch.device("cpu")

        if requested_device == "cuda":
            if not torch.cuda.is_available():
                raise ModelConfigurationError(
                    "CUDA foi solicitado, mas não está disponível."
                )

            return torch.device("cuda")

        if torch.cuda.is_available():
            return torch.device("cuda")

        return torch.device("cpu")


__all__ = [
    "BaseSentimentModel",
    "CANONICAL_SENTIMENT_LABELS",
    "ModelConfigurationError",
    "ModelLoadingError",
    "ModelPrediction",
    "ModelPredictionError",
]
