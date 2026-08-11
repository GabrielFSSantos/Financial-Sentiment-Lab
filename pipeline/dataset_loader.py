"""Carregamento e padronização dos datasets da pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast

import pandas as pd

from pipeline.common import ASSET_FETCH_HINT, CANONICAL_LABELS
from pipeline.configuration import DatasetConfiguration


CONFIGURABLE_FIELDS: tuple[str, ...] = (
    "news_id",
    "text",
    "date",
    "company",
    "sector",
    "ticker",
    "title",
    "true_label",
    "source",
    "url",
)

STANDARD_COLUMNS: tuple[str, ...] = (
    "dataset_key",
    "dataset_name",
    "news_id",
    "text",
    "date",
    "company",
    "sector",
    "ticker",
    "title",
    "true_label",
    "source",
    "url",
    "source_row_number",
)

OPTIONAL_TEXT_FIELDS: tuple[str, ...] = (
    "company",
    "sector",
    "ticker",
    "title",
    "source",
    "url",
)

SUPPORTED_FORMATS: frozenset[str] = frozenset(
    {"csv", "jsonl", "parquet", "huggingface"}
)


class DatasetError(RuntimeError):
    """Erro-base relacionado ao carregamento de datasets."""


class DatasetFileError(DatasetError):
    """Erro de acesso ou leitura do arquivo de entrada."""


class DatasetValidationError(DatasetError):
    """Erro encontrado ao validar ou normalizar os dados."""


@dataclass(frozen=True)
class DatasetLoadStatistics:
    """Estatísticas produzidas durante o carregamento."""

    original_row_count: int
    valid_row_count: int
    dropped_empty_text_count: int
    duplicate_id_count: int
    duplicate_ids_resolved: int
    invalid_date_count: int
    labeled_row_count: int
    unlabeled_row_count: int
    original_column_count: int
    output_column_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "original_row_count": self.original_row_count,
            "valid_row_count": self.valid_row_count,
            "dropped_empty_text_count": self.dropped_empty_text_count,
            "duplicate_id_count": self.duplicate_id_count,
            "duplicate_ids_resolved": self.duplicate_ids_resolved,
            "invalid_date_count": self.invalid_date_count,
            "labeled_row_count": self.labeled_row_count,
            "unlabeled_row_count": self.unlabeled_row_count,
            "original_column_count": self.original_column_count,
            "output_column_count": self.output_column_count,
        }


@dataclass
class LoadedDataset:
    """Dataset carregado e convertido para o schema interno."""

    configuration: DatasetConfiguration
    dataframe: pd.DataFrame
    statistics: DatasetLoadStatistics
    original_columns: tuple[str, ...]
    extra_columns: tuple[str, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def key(self) -> str:
        return self.configuration.key

    @property
    def dataset_name(self) -> str:
        return self.configuration.dataset_name

    @property
    def display_name(self) -> str:
        return self.configuration.display_name

    @property
    def has_labels(self) -> bool:
        return bool(self.configuration.labels.get("available", False))

    @property
    def has_dates(self) -> bool:
        return bool(self.configuration.dates.get("available", False))

    @property
    def texts(self) -> list[str]:
        """Retorna os textos válidos na mesma ordem do DataFrame."""

        return self.dataframe["text"].astype(str).tolist()

    def metadata(self) -> dict[str, Any]:
        """Retorna metadados serializáveis para a saída da combinação."""

        label_distribution: dict[str, int] = {}
        if "true_label" in self.dataframe.columns:
            counts = self.dataframe["true_label"].value_counts(dropna=True)
            label_distribution = {
                str(label): int(count)
                for label, count in counts.items()
            }

        return {
            "dataset_key": self.key,
            "dataset_name": self.dataset_name,
            "display_name": self.display_name,
            "path": (
                str(self.configuration.path)
                if self.configuration.path is not None
                else None
            ),
            "format": self.configuration.format,
            "has_labels": self.has_labels,
            "has_dates": self.has_dates,
            "statistics": self.statistics.to_dict(),
            "original_columns": list(self.original_columns),
            "extra_columns": list(self.extra_columns),
            "label_distribution": label_distribution,
            "warnings": list(self.warnings),
            "configured_metadata": dict(self.configuration.metadata),
        }


class DatasetLoader:
    """Carrega datasets já resolvidos por ``ConfigurationLoader``."""

    def __init__(self, *, copy_dataframe: bool = False) -> None:
        self.copy_dataframe = bool(copy_dataframe)

    def validate_file(self, configuration: DatasetConfiguration) -> None:
        """Valida somente o arquivo e o formato, sem carregar os dados."""

        if configuration.format not in SUPPORTED_FORMATS:
            raise DatasetValidationError(
                f"Formato não suportado no dataset {configuration.key!r}: "
                f"{configuration.format!r}. Formatos aceitos: "
                f"{sorted(SUPPORTED_FORMATS)}."
            )

        if configuration.format == "huggingface":
            if not configuration.source:
                raise DatasetValidationError(
                    f"Dataset {configuration.key!r} usa format=huggingface "
                    "sem source configurado."
                )
            return

        path = configuration.path
        if path is None:
            raise DatasetFileError(
                f"Dataset {configuration.key!r} não possui path configurado."
            )

        if not path.exists():
            hint = (
                ASSET_FETCH_HINT
                if configuration.source
                else ""
            )
            raise DatasetFileError(
                f"Arquivo do dataset {configuration.key!r} não encontrado: "
                f"{path}.{hint}"
            )

        if not path.is_file():
            raise DatasetFileError(
                f"O caminho do dataset {configuration.key!r} não é um "
                f"arquivo: {path}"
            )

    def inspect_columns(
        self,
        configuration: DatasetConfiguration,
    ) -> tuple[str, ...]:
        """Lê o cabeçalho (e aplica text_compose, se houver)."""

        self.validate_file(configuration)
        dataframe = self._read_dataset(configuration, nrows=0)
        if configuration.text_compose is not None:
            dataframe = self._apply_text_compose(configuration, dataframe)
        columns = tuple(str(column) for column in dataframe.columns)
        self._validate_source_columns(configuration, columns)
        return columns

    def load(self, configuration: DatasetConfiguration) -> LoadedDataset:
        """Carrega, valida, limpa e padroniza um dataset."""

        self.validate_file(configuration)

        source = self._read_dataset(configuration)
        source = self._apply_text_compose(configuration, source)
        source = self._apply_limits(configuration, source)
        original_columns = tuple(str(column) for column in source.columns)
        original_row_count = len(source)

        if original_row_count == 0:
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} não possui linhas."
            )

        self._validate_source_columns(configuration, original_columns)

        # Número lógico da linha no arquivo de origem. No CSV com header=0,
        # a primeira linha de dados é a 2; no JSONL, cada objeto ocupa sua
        # própria linha e o primeiro registro está na linha 1.
        header = (
            int(configuration.reader.get("header", 0)) + 1
            if configuration.format == "csv"
            else 0
        )
        source_row_number = pd.Series(
            range(header + 1, header + 1 + original_row_count),
            index=source.index,
            dtype="Int64",
        )

        standardized = self._map_standard_columns(
            configuration,
            source,
            source_row_number,
        )

        standardized, dropped_empty_text_count = self._normalize_texts(
            configuration,
            standardized,
        )

        if standardized.empty:
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} não possui textos válidos "
                "após a limpeza."
            )

        standardized = self._normalize_ids(configuration, standardized)
        duplicate_id_count = self._count_duplicate_ids(standardized)
        duplicate_ids_resolved = self._handle_duplicate_ids(
            configuration,
            standardized,
            duplicate_id_count,
        )

        invalid_date_count = self._normalize_dates(
            configuration,
            standardized,
        )
        self._normalize_labels(configuration, standardized)
        self._normalize_optional_fields(standardized)

        preserve_extra = bool(
            configuration.validation.get("preserve_extra_columns", True)
        )
        extra_columns: tuple[str, ...] = ()

        if preserve_extra:
            standardized, extra_columns = self._append_extra_columns(
                configuration,
                source,
                standardized,
            )

        standardized = self._order_columns(standardized)
        standardized.reset_index(drop=True, inplace=True)

        if self.copy_dataframe:
            standardized = standardized.copy(deep=True)

        labeled_row_count = int(
            standardized["true_label"].notna().sum()
        )
        valid_row_count = len(standardized)

        statistics = DatasetLoadStatistics(
            original_row_count=original_row_count,
            valid_row_count=valid_row_count,
            dropped_empty_text_count=dropped_empty_text_count,
            duplicate_id_count=duplicate_id_count,
            duplicate_ids_resolved=duplicate_ids_resolved,
            invalid_date_count=invalid_date_count,
            labeled_row_count=labeled_row_count,
            unlabeled_row_count=valid_row_count - labeled_row_count,
            original_column_count=len(original_columns),
            output_column_count=len(standardized.columns),
        )

        warnings = self._build_warnings(
            configuration=configuration,
            statistics=statistics,
        )

        return LoadedDataset(
            configuration=configuration,
            dataframe=standardized,
            statistics=statistics,
            original_columns=original_columns,
            extra_columns=extra_columns,
            warnings=warnings,
        )

    def _read_dataset(
        self,
        configuration: DatasetConfiguration,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        effective_nrows = nrows
        if effective_nrows is None:
            max_rows = configuration.limits.get("max_rows")
            if isinstance(max_rows, int) and max_rows > 0:
                effective_nrows = max_rows

        if configuration.format == "csv":
            return self._read_csv(
                configuration,
                nrows=effective_nrows,
            )
        if configuration.format == "jsonl":
            return self._read_jsonl(
                configuration,
                nrows=effective_nrows,
            )
        if configuration.format == "parquet":
            return self._read_parquet(
                configuration,
                nrows=effective_nrows,
            )
        if configuration.format == "huggingface":
            return self._read_huggingface(
                configuration,
                nrows=effective_nrows,
            )
        raise DatasetValidationError(
            f"Formato não suportado no dataset {configuration.key!r}: "
            f"{configuration.format!r}."
        )

    def _read_parquet(
        self,
        configuration: DatasetConfiguration,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        if configuration.path is None:
            raise DatasetFileError(
                f"Dataset {configuration.key!r} não possui path configurado."
            )

        try:
            dataframe = pd.read_parquet(configuration.path)
        except (OSError, ValueError) as error:
            raise DatasetFileError(
                f"Falha ao ler parquet do dataset {configuration.key!r} em "
                f"{configuration.path}: {error}"
            ) from error

        if nrows is not None:
            dataframe = dataframe.head(nrows)

        return self._normalize_source_columns(dataframe, configuration)

    def _read_huggingface(
        self,
        configuration: DatasetConfiguration,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        source = configuration.source
        if not source:
            raise DatasetValidationError(
                f"Dataset {configuration.key!r} usa format=huggingface "
                "sem source."
            )

        try:
            from datasets import load_dataset
        except ImportError as error:
            raise DatasetFileError(
                "Biblioteca datasets não instalada. "
                "Execute: pip install datasets"
            ) from error

        split = source.get("split", "train")
        try:
            dataset = load_dataset(
                source["repo_id"],
                source.get("config", "default"),
                split=split,
                revision=source.get("revision", "main"),
            )
        except Exception as error:
            raise DatasetFileError(
                f"Falha ao carregar dataset HF {configuration.key!r}: "
                f"{error}"
            ) from error

        if nrows is not None:
            dataset = dataset.select(range(min(nrows, len(dataset))))

        dataframe = dataset.to_pandas()
        return self._normalize_source_columns(dataframe, configuration)

    @staticmethod
    def _normalize_source_columns(
        dataframe: pd.DataFrame,
        configuration: DatasetConfiguration,
    ) -> pd.DataFrame:
        dataframe = dataframe.copy()
        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

        if len(set(dataframe.columns)) != len(dataframe.columns):
            duplicates = _duplicates(dataframe.columns)
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui nomes de colunas "
                f"duplicados: {duplicates}."
            )

        return dataframe

    def _apply_text_compose(
        self,
        configuration: DatasetConfiguration,
        source: pd.DataFrame,
    ) -> pd.DataFrame:
        compose = configuration.text_compose
        if compose is None:
            return source

        template = str(compose["template"])
        fields = compose["fields"]
        skip_if_all_empty = bool(compose.get("skip_if_all_empty", True))

        composed_values: list[str | None] = []
        for row_index in source.index:
            values: dict[str, str] = {}
            all_empty = True
            for placeholder, column_name in fields.items():
                raw = source.at[row_index, column_name]
                if pd.isna(raw):
                    text_value = ""
                else:
                    text_value = str(raw).strip()
                if text_value:
                    all_empty = False
                values[placeholder] = text_value

            if skip_if_all_empty and all_empty:
                composed_values.append(None)
            else:
                composed_values.append(template.format(**values))

        output = source.copy()
        output["__composed_text__"] = pd.Series(
            composed_values,
            index=source.index,
            dtype="string",
        )
        return output

    def _apply_limits(
        self,
        configuration: DatasetConfiguration,
        source: pd.DataFrame,
    ) -> pd.DataFrame:
        limits = configuration.limits
        if not limits:
            return source

        filtered = source
        date_column = configuration.columns.get("date")
        date_from = limits.get("date_from")
        date_to = limits.get("date_to")

        if (
            date_column
            and date_column in filtered.columns
            and (date_from or date_to)
        ):
            parsed = pd.to_datetime(
                filtered[date_column],
                errors="coerce",
                utc=True,
            )
            mask = pd.Series(True, index=filtered.index)
            if date_from:
                lower = pd.to_datetime(date_from, errors="coerce", utc=True)
                if pd.notna(lower):
                    mask &= parsed >= lower
            if date_to:
                upper = pd.to_datetime(date_to, errors="coerce", utc=True)
                if pd.notna(upper):
                    mask &= parsed <= upper
            filtered = filtered.loc[mask]

        return filtered.reset_index(drop=True)

    def _read_csv(
        self,
        configuration: DatasetConfiguration,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        reader = configuration.reader

        kwargs: dict[str, Any] = {
            "encoding": reader.get("encoding", "utf-8"),
            "sep": reader.get("delimiter", ","),
            "quotechar": reader.get("quotechar", '"'),
            "header": reader.get("header", 0),
            "low_memory": bool(reader.get("low_memory", False)),
            "skip_blank_lines": bool(reader.get("skip_blank_lines", True)),
            "on_bad_lines": reader.get("on_bad_lines", "error"),
            # Lê os dados como texto para evitar perda de zeros à esquerda
            # em IDs e tickers. Datas e rótulos são normalizados depois.
            "dtype": "string",
            "keep_default_na": True,
        }

        if nrows is not None:
            kwargs["nrows"] = nrows

        try:
            dataframe = pd.read_csv(configuration.path, **kwargs)
        except UnicodeDecodeError as error:
            raise DatasetFileError(
                f"Não foi possível decodificar o dataset "
                f"{configuration.key!r} com "
                f"encoding={kwargs['encoding']!r}: {error}"
            ) from error
        except (OSError, ValueError, pd.errors.ParserError) as error:
            raise DatasetFileError(
                f"Falha ao ler o dataset {configuration.key!r} em "
                f"{configuration.path}: {error}"
            ) from error

        dataframe.columns = [str(column).strip() for column in dataframe.columns]

        if len(set(dataframe.columns)) != len(dataframe.columns):
            duplicates = _duplicates(dataframe.columns)
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui nomes de colunas "
                f"duplicados: {duplicates}."
            )

        return dataframe

    def _read_jsonl(
        self,
        configuration: DatasetConfiguration,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        encoding = configuration.reader.get("encoding", "utf-8")

        try:
            dataframe = pd.read_json(
                configuration.path,
                lines=True,
                encoding=encoding,
                nrows=nrows,
                dtype=False,
                convert_dates=False,
            )
        except UnicodeDecodeError as error:
            raise DatasetFileError(
                f"Não foi possível decodificar o dataset "
                f"{configuration.key!r} com encoding={encoding!r}: {error}"
            ) from error
        except (OSError, ValueError) as error:
            raise DatasetFileError(
                f"Falha ao ler o dataset {configuration.key!r} em "
                f"{configuration.path}: {error}"
            ) from error

        dataframe.columns = [str(column).strip() for column in dataframe.columns]

        if len(set(dataframe.columns)) != len(dataframe.columns):
            duplicates = _duplicates(dataframe.columns)
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui nomes de colunas "
                f"duplicados: {duplicates}."
            )

        return dataframe

    def _validate_source_columns(
        self,
        configuration: DatasetConfiguration,
        source_columns: Sequence[str],
    ) -> None:
        available = set(source_columns)
        missing: list[str] = []

        for internal_field in configuration.required_fields:
            if internal_field == "text" and configuration.text_compose:
                if "__composed_text__" not in available:
                    missing.append("text -> __composed_text__")
                continue

            source_name = configuration.columns.get(internal_field)
            if not source_name or source_name not in available:
                missing.append(
                    f"{internal_field} -> {source_name!r}"
                )

        # Colunas opcionais configuradas também precisam existir. Para omitir
        # uma informação, a configuração deve usar null explicitamente.
        configured_missing = [
            f"{internal} -> {source_name!r}"
            for internal, source_name in configuration.columns.items()
            if source_name is not None and source_name not in available
        ]

        all_missing = sorted(set(missing + configured_missing))
        if all_missing:
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} não possui colunas "
                f"configuradas: {all_missing}. Colunas disponíveis: "
                f"{sorted(available)}."
            )

    def _map_standard_columns(
        self,
        configuration: DatasetConfiguration,
        source: pd.DataFrame,
        source_row_number: pd.Series,
    ) -> pd.DataFrame:
        result = pd.DataFrame(index=source.index)
        result["dataset_key"] = configuration.key
        result["dataset_name"] = configuration.dataset_name

        for field_name in CONFIGURABLE_FIELDS:
            source_name = configuration.columns.get(field_name)
            if field_name == "text" and configuration.text_compose is not None:
                result[field_name] = source["__composed_text__"].astype(
                    "string"
                )
            elif source_name is None:
                result[field_name] = pd.Series(
                    pd.NA,
                    index=source.index,
                    dtype="string",
                )
            else:
                result[field_name] = source[source_name].astype("string")

        result["source_row_number"] = source_row_number
        return result

    def _normalize_texts(
        self,
        configuration: DatasetConfiguration,
        dataframe: pd.DataFrame,
    ) -> tuple[pd.DataFrame, int]:
        strip_text = bool(configuration.validation.get("strip_text", True))
        drop_empty = bool(
            configuration.validation.get("drop_empty_texts", True)
        )

        text = dataframe["text"].astype("string")
        if strip_text:
            text = text.str.strip()

        text = text.mask(text.eq(""), pd.NA)
        dataframe["text"] = text
        empty_mask = dataframe["text"].isna()
        empty_count = int(empty_mask.sum())

        if empty_count == 0:
            return dataframe, 0

        if not drop_empty:
            rows = dataframe.loc[empty_mask, "source_row_number"].tolist()
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui {empty_count} "
                f"texto(s) vazio(s) nas linhas {rows[:20]}. "
                "Habilite validation.drop_empty_texts para removê-los."
            )

        return dataframe.loc[~empty_mask].copy(), empty_count

    def _normalize_ids(
        self,
        configuration: DatasetConfiguration,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        ids = dataframe["news_id"].astype("string").str.strip()
        ids = ids.mask(ids.eq(""), pd.NA)
        missing_mask = ids.isna()

        if missing_mask.any():
            rows = dataframe.loc[missing_mask, "source_row_number"].tolist()
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui "
                f"{int(missing_mask.sum())} news_id vazio(s) nas linhas "
                f"{rows[:20]}."
            )

        dataframe["news_id"] = ids
        return dataframe

    @staticmethod
    def _count_duplicate_ids(dataframe: pd.DataFrame) -> int:
        return int(dataframe["news_id"].duplicated(keep=False).sum())

    def _handle_duplicate_ids(
        self,
        configuration: DatasetConfiguration,
        dataframe: pd.DataFrame,
        duplicate_count: int,
    ) -> int:
        if duplicate_count == 0:
            return 0

        duplicated = dataframe["news_id"].duplicated(keep=False)
        duplicate_values = (
            dataframe.loc[duplicated, "news_id"]
            .drop_duplicates()
            .astype(str)
            .tolist()
        )

        fail = bool(
            configuration.validation.get("fail_on_duplicate_ids", True)
        )
        if fail:
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui IDs duplicados: "
                f"{duplicate_values[:20]}. Total de linhas envolvidas: "
                f"{duplicate_count}."
            )

        occurrence = dataframe.groupby("news_id", sort=False).cumcount()
        repeated_mask = occurrence.gt(0)
        dataframe.loc[repeated_mask, "news_id"] = (
            dataframe.loc[repeated_mask, "news_id"].astype(str)
            + "__dup"
            + occurrence.loc[repeated_mask].astype(str)
        )
        return int(repeated_mask.sum())

    def _normalize_dates(
        self,
        configuration: DatasetConfiguration,
        dataframe: pd.DataFrame,
    ) -> int:
        dates_config = configuration.dates
        available = bool(dates_config.get("available", False))

        if not available:
            dataframe["date"] = pd.Series(
                pd.NA,
                index=dataframe.index,
                dtype="string",
            )
            return 0

        raw_dates = dataframe["date"].astype("string").str.strip()
        raw_dates = raw_dates.mask(raw_dates.eq(""), pd.NA)
        expected_format = dates_config.get("format")
        dayfirst = bool(dates_config.get("dayfirst", False))

        try:
            parsed = pd.to_datetime(
                raw_dates,
                format=expected_format,
                dayfirst=dayfirst,
                errors="coerce",
                utc=True,
            )
        except (TypeError, ValueError) as error:
            raise DatasetValidationError(
                f"Falha ao interpretar datas do dataset "
                f"{configuration.key!r}: {error}"
            ) from error

        invalid_mask = raw_dates.notna() & parsed.isna()
        invalid_count = int(invalid_mask.sum())
        missing_count = int(raw_dates.isna().sum())
        fail_on_invalid = bool(dates_config.get("fail_on_invalid", True))

        if fail_on_invalid and (invalid_count > 0 or missing_count > 0):
            invalid_values = raw_dates.loc[invalid_mask].drop_duplicates().tolist()
            missing_rows = dataframe.loc[
                raw_dates.isna(), "source_row_number"
            ].tolist()
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui datas inválidas "
                f"ou ausentes. Inválidas: {invalid_values[:20]}; "
                f"linhas sem data: {missing_rows[:20]}. Formato esperado: "
                f"{expected_format!r}."
            )

        output_format = str(dates_config.get("output_format", "%Y-%m-%d"))
        if parsed.dt.tz is not None:
            parsed = parsed.dt.tz_convert(None)
        formatted = parsed.dt.strftime(output_format).astype("string")
        dataframe["date"] = formatted
        return invalid_count + missing_count

    def _normalize_labels(
        self,
        configuration: DatasetConfiguration,
        dataframe: pd.DataFrame,
    ) -> None:
        labels_config = configuration.labels
        available = bool(labels_config.get("available", False))

        if not available:
            dataframe["true_label"] = pd.Series(
                pd.NA,
                index=dataframe.index,
                dtype="string",
            )
            return

        labels = dataframe["true_label"].astype("string")
        if bool(labels_config.get("strip_whitespace", True)):
            labels = labels.str.strip()
        labels = labels.mask(labels.eq(""), pd.NA)

        normalize_case = bool(labels_config.get("normalize_case", True))
        normalized_input = cast(
            pd.Series,
            labels.str.lower() if normalize_case else labels,
        )

        raw_mapping = labels_config.get("mapping", {})
        mapping: dict[str, str] = {}
        for source_value, target_value in raw_mapping.items():
            key = str(source_value).strip()
            if normalize_case:
                key = key.lower()
            mapping[key] = str(target_value).strip().upper()

        mapped = normalized_input.map(
            lambda value: (
                pd.NA
                if pd.isna(value)
                else mapping.get(str(value), pd.NA)
            )
        ).astype("string")
        missing_mask = cast(pd.Series, labels.isna())
        unknown_mask = cast(
            pd.Series,
            labels.notna() & mapped.isna(),
        )

        if bool(missing_mask.any()) or bool(unknown_mask.any()):
            unknown_values = labels.loc[unknown_mask].drop_duplicates().tolist()
            missing_rows = dataframe.loc[
                missing_mask, "source_row_number"
            ].tolist()
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} possui rótulos ausentes "
                f"ou não mapeados. Não mapeados: {unknown_values[:20]}; "
                f"linhas sem rótulo: {missing_rows[:20]}."
            )

        invalid_targets = sorted(set(mapped.dropna()) - set(CANONICAL_LABELS))
        if invalid_targets:
            raise DatasetValidationError(
                f"O dataset {configuration.key!r} gerou classes inválidas: "
                f"{invalid_targets}."
            )

        dataframe["true_label"] = mapped

    @staticmethod
    def _normalize_optional_fields(dataframe: pd.DataFrame) -> None:
        for field_name in OPTIONAL_TEXT_FIELDS:
            values = dataframe[field_name].astype("string").str.strip()
            dataframe[field_name] = values.mask(values.eq(""), pd.NA)

    def _append_extra_columns(
        self,
        configuration: DatasetConfiguration,
        source: pd.DataFrame,
        standardized: pd.DataFrame,
    ) -> tuple[pd.DataFrame, tuple[str, ...]]:
        mapped_source_columns = {
            source_name
            for source_name in configuration.columns.values()
            if source_name is not None
        }
        extra_source_columns = [
            column
            for column in source.columns
            if column not in mapped_source_columns
        ]

        # Após a remoção de textos vazios, standardized mantém os índices
        # originais, permitindo alinhar as colunas extras com segurança.
        output_names: list[str] = []
        for source_name in extra_source_columns:
            output_name = str(source_name)
            if output_name in standardized.columns:
                output_name = f"source__{output_name}"

            base_name = output_name
            suffix = 2
            while output_name in standardized.columns:
                output_name = f"{base_name}_{suffix}"
                suffix += 1

            standardized[output_name] = source.loc[
                standardized.index, source_name
            ].astype("string")
            output_names.append(output_name)

        return standardized, tuple(output_names)

    @staticmethod
    def _order_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
        standard = [
            column for column in STANDARD_COLUMNS if column in dataframe.columns
        ]
        extra = [
            column for column in dataframe.columns if column not in standard
        ]
        return dataframe.loc[:, standard + extra]

    @staticmethod
    def _build_warnings(
        *,
        configuration: DatasetConfiguration,
        statistics: DatasetLoadStatistics,
    ) -> tuple[str, ...]:
        warnings: list[str] = []

        if statistics.dropped_empty_text_count:
            warnings.append(
                f"{statistics.dropped_empty_text_count} linha(s) com texto "
                "vazio foram removidas."
            )

        if statistics.duplicate_ids_resolved:
            warnings.append(
                f"{statistics.duplicate_ids_resolved} ID(s) duplicado(s) "
                "foram renomeados."
            )

        if statistics.invalid_date_count:
            warnings.append(
                f"{statistics.invalid_date_count} data(s) inválida(s) ou "
                "ausente(s) foram mantidas como valor nulo."
            )

        if not configuration.labels.get("available", False):
            warnings.append(
                "O dataset não possui rótulos verdadeiros; métricas "
                "supervisionadas não serão calculadas."
            )

        if not configuration.dates.get("available", False):
            warnings.append(
                "O dataset não possui data; agregações temporais serão "
                "ignoradas quando exigirem essa coluna."
            )

        return tuple(warnings)


def _duplicates(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []

    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)

    return duplicates


__all__ = [
    "CANONICAL_LABELS",
    "CONFIGURABLE_FIELDS",
    "DatasetError",
    "DatasetFileError",
    "DatasetLoadStatistics",
    "DatasetLoader",
    "DatasetValidationError",
    "LoadedDataset",
    "STANDARD_COLUMNS",
]
