"""Registro, validação e criação dinâmica dos modelos.

Este módulo recebe configurações já resolvidas por
``pipeline.configuration``. Ele não lê arquivos YAML e não escolhe quais
modelos participarão do experimento.

Responsabilidades:

- registrar os modelos selecionados;
- importar dinamicamente os adaptadores;
- validar o contrato com ``BaseSentimentModel``;
- validar os arquivos locais declarados em ``models.yaml``;
- montar e validar os argumentos do construtor;
- criar instâncias sem carregar os pesos antecipadamente;
- carregar, reutilizar e liberar modelos quando solicitado;
- fornecer metadados padronizados ao runner.

A seleção dos modelos permanece centralizada em ``configs/models.yaml``.
"""

from __future__ import annotations

import copy
import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from models.base_model import BaseSentimentModel, ModelPrediction
from pipeline.common import to_serializable
from pipeline.configuration import (
    ModelConfiguration,
    ResolvedConfiguration,
)


RESERVED_CONSTRUCTOR_ARGUMENTS = frozenset(
    {
        "model_name",
        "model_dir",
        "model_configuration",
        "loading",
        "validation",
    }
)


class ModelRegistryError(RuntimeError):
    """Erro-base relacionado ao registro ou criação de modelos."""


class ModelNotRegisteredError(ModelRegistryError, KeyError):
    """Modelo solicitado não está registrado."""


class ModelAdapterImportError(ModelRegistryError, ImportError):
    """O adaptador configurado não pôde ser importado."""


class ModelAdapterContractError(ModelRegistryError, TypeError):
    """O adaptador não atende ao contrato da classe-base."""


class ModelFileValidationError(ModelRegistryError, FileNotFoundError):
    """Os arquivos locais exigidos pelo modelo não foram encontrados."""


class ModelInstantiationError(ModelRegistryError):
    """O adaptador não pôde ser instanciado."""


@dataclass
class RegisteredModel:
    """Instância de modelo criada a partir de uma configuração resolvida."""

    configuration: ModelConfiguration
    adapter_class: type[BaseSentimentModel]
    instance: BaseSentimentModel
    constructor_arguments: dict[str, Any]

    @property
    def key(self) -> str:
        return self.configuration.key

    @property
    def model_name(self) -> str:
        return self.configuration.model_name

    @property
    def display_name(self) -> str:
        return self.configuration.display_name

    @property
    def is_loaded(self) -> bool:
        return bool(self.instance.is_loaded)

    @property
    def device_type(self) -> str:
        return self.instance.device_type

    @property
    def device_name(self) -> str:
        return self.instance.device_name

    def load(
        self,
        *,
        skip_file_validation: bool = False,
    ) -> None:
        """Carrega tokenizer e pesos caso ainda não estejam carregados."""

        self.instance.load(
            skip_file_validation=skip_file_validation
        )

    def predict(
        self,
        texts: Sequence[str],
    ) -> list[ModelPrediction]:
        """Executa inferência preservando a ordem dos textos."""

        return self.instance.predict(texts)

    def unload(self) -> None:
        """Libera tokenizer, pesos e memória associada ao modelo."""

        self.instance.unload()

    def metadata(self) -> dict[str, Any]:
        """Combina configuração, adaptador e informações de execução."""

        constructor_arguments = {
            key: to_serializable(value)
            for key, value in self.constructor_arguments.items()
            if key not in {
                "model_configuration",
                "loading",
                "validation",
            }
        }

        return {
            "model_key": self.key,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "adapter": self.configuration.adapter,
            "adapter_module": self.adapter_class.__module__,
            "adapter_class": self.adapter_class.__name__,
            "model_dir": str(self.configuration.model_dir),
            "parameters": copy.deepcopy(self.configuration.parameters),
            "loading": copy.deepcopy(self.configuration.loading),
            "validation": copy.deepcopy(self.configuration.validation),
            "configured_metadata": copy.deepcopy(
                self.configuration.metadata
            ),
            "constructor_arguments": constructor_arguments,
            "runtime": to_serializable(
                self.instance.get_metadata()
            ),
        }


class ModelRegistry:
    """Administra adaptadores e instâncias dos modelos selecionados."""

    def __init__(
        self,
        configurations: Iterable[ModelConfiguration],
    ) -> None:
        configuration_list = tuple(configurations)

        if not configuration_list:
            raise ModelRegistryError(
                "Nenhum modelo foi fornecido ao ModelRegistry."
            )

        self._configurations: dict[str, ModelConfiguration] = {}
        self._adapter_cache: dict[
            str,
            type[BaseSentimentModel],
        ] = {}
        self._instances: dict[str, RegisteredModel] = {}

        for configuration in configuration_list:
            if not isinstance(
                configuration,
                ModelConfiguration,
            ):
                raise ModelRegistryError(
                    "Todas as entradas do registry precisam ser "
                    "instâncias de ModelConfiguration."
                )

            if configuration.key in self._configurations:
                raise ModelRegistryError(
                    f"Modelo registrado mais de uma vez: "
                    f"{configuration.key!r}."
                )

            self._configurations[configuration.key] = configuration

    @classmethod
    def from_resolved_configuration(
        cls,
        configuration: ResolvedConfiguration,
    ) -> "ModelRegistry":
        """Cria o registry com os modelos selecionados no experimento."""

        return cls(configuration.models)

    @property
    def keys(self) -> tuple[str, ...]:
        """Chaves dos modelos na ordem resolvida."""

        return tuple(self._configurations)

    @property
    def configurations(
        self,
    ) -> tuple[ModelConfiguration, ...]:
        return tuple(self._configurations.values())

    @property
    def instantiated_keys(self) -> tuple[str, ...]:
        return tuple(self._instances)

    def __contains__(self, key: object) -> bool:
        return key in self._configurations

    def __len__(self) -> int:
        return len(self._configurations)

    def get_configuration(
        self,
        key: str,
    ) -> ModelConfiguration:
        """Retorna a configuração registrada para uma chave."""

        normalized_key = str(key).strip()

        try:
            return self._configurations[normalized_key]
        except KeyError as error:
            available = ", ".join(self.keys)
            raise ModelNotRegisteredError(
                f"Modelo não registrado: {normalized_key!r}. "
                f"Disponíveis: {available}."
            ) from error

    def resolve_adapter_class(
        self,
        model: str | ModelConfiguration,
    ) -> type[BaseSentimentModel]:
        """Importa e valida a classe configurada como adaptador."""

        configuration = self._resolve_configuration(model)

        cached = self._adapter_cache.get(configuration.key)
        if cached is not None:
            return cached

        module_name, class_name = self._split_adapter_path(
            configuration
        )

        try:
            module = importlib.import_module(module_name)
        except Exception as error:
            raise ModelAdapterImportError(
                f"Não foi possível importar o módulo "
                f"{module_name!r} do modelo "
                f"{configuration.key!r}: {error}"
            ) from error

        try:
            adapter_candidate = getattr(module, class_name)
        except AttributeError as error:
            raise ModelAdapterImportError(
                f"O módulo {module_name!r} não possui a classe "
                f"{class_name!r}, configurada para o modelo "
                f"{configuration.key!r}."
            ) from error

        if not inspect.isclass(adapter_candidate):
            raise ModelAdapterContractError(
                f"O adaptador {configuration.adapter!r} não é uma "
                "classe Python."
            )

        if adapter_candidate is BaseSentimentModel:
            raise ModelAdapterContractError(
                f"O modelo {configuration.key!r} não pode usar "
                "BaseSentimentModel diretamente."
            )

        if not issubclass(
            adapter_candidate,
            BaseSentimentModel,
        ):
            raise ModelAdapterContractError(
                f"O adaptador {configuration.adapter!r} precisa "
                "herdar de models.base_model.BaseSentimentModel."
            )

        if inspect.isabstract(adapter_candidate):
            abstract_methods = sorted(
                adapter_candidate.__abstractmethods__
            )
            raise ModelAdapterContractError(
                f"O adaptador {configuration.adapter!r} ainda é "
                f"abstrato. Métodos pendentes: {abstract_methods}."
            )

        self._adapter_cache[configuration.key] = adapter_candidate
        return adapter_candidate

    def validate_files(
        self,
        model: str | ModelConfiguration,
    ) -> tuple[Path, ...]:
        """Valida o diretório e os arquivos declarados no YAML."""

        configuration = self._resolve_configuration(model)
        model_dir = configuration.model_dir

        require_directory = bool(
            configuration.validation.get(
                "require_model_directory",
                True,
            )
        )
        require_files = bool(
            configuration.validation.get(
                "require_required_files",
                True,
            )
        )

        if require_directory:
            if not model_dir.exists():
                raise ModelFileValidationError(
                    f"Diretório do modelo "
                    f"{configuration.key!r} não encontrado: "
                    f"{model_dir}"
                )

            if not model_dir.is_dir():
                raise ModelFileValidationError(
                    f"O caminho do modelo "
                    f"{configuration.key!r} não é um diretório: "
                    f"{model_dir}"
                )

        if not require_files:
            return tuple()

        validated_paths: list[Path] = []
        missing_paths: list[Path] = []

        for relative_name in configuration.required_files:
            relative_path = Path(relative_name)

            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
            ):
                raise ModelFileValidationError(
                    f"Arquivo obrigatório inválido no modelo "
                    f"{configuration.key!r}: {relative_name!r}. "
                    "O caminho precisa ser relativo e não pode "
                    "conter '..'."
                )

            candidate = model_dir / relative_path

            if not candidate.is_file():
                missing_paths.append(candidate)
            else:
                validated_paths.append(candidate)

        if missing_paths:
            formatted = "\n".join(
                f"  - {path}"
                for path in missing_paths
            )
            raise ModelFileValidationError(
                f"Arquivos obrigatórios ausentes no modelo "
                f"{configuration.key!r}:\n{formatted}"
            )

        return tuple(validated_paths)

    def build_constructor_arguments(
        self,
        model: str | ModelConfiguration,
        *,
        parameter_overrides: Mapping[str, Any] | None = None,
        adapter_class: type[BaseSentimentModel] | None = None,
    ) -> dict[str, Any]:
        """Monta e valida os argumentos enviados ao adaptador."""

        configuration = self._resolve_configuration(model)
        resolved_adapter = (
            adapter_class
            or self.resolve_adapter_class(configuration)
        )

        arguments = copy.deepcopy(
            configuration.parameters
        )

        if parameter_overrides is not None:
            if not isinstance(parameter_overrides, Mapping):
                raise ModelInstantiationError(
                    "parameter_overrides precisa ser um mapeamento."
                )

            normalized_overrides = dict(parameter_overrides)
            reserved = (
                set(normalized_overrides)
                & RESERVED_CONSTRUCTOR_ARGUMENTS
            )

            if reserved:
                raise ModelInstantiationError(
                    "Os seguintes argumentos são reservados e não "
                    "podem ser sobrescritos: "
                    f"{sorted(reserved)}."
                )

            arguments.update(normalized_overrides)

        arguments["model_name"] = configuration.model_name
        arguments["model_dir"] = configuration.model_dir

        signature = self._get_constructor_signature(
            resolved_adapter
        )
        parameters = signature.parameters

        # Adaptadores futuros podem optar por receber a configuração
        # completa ou apenas as seções de carregamento e validação.
        if "model_configuration" in parameters:
            arguments["model_configuration"] = configuration

        if "loading" in parameters:
            arguments["loading"] = copy.deepcopy(
                configuration.loading
            )

        if "validation" in parameters:
            arguments["validation"] = copy.deepcopy(
                configuration.validation
            )

        try:
            signature.bind(**arguments)
        except TypeError as error:
            accepted = [
                name
                for name, parameter in parameters.items()
                if name != "self"
                and parameter.kind
                not in {
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                }
            ]
            raise ModelInstantiationError(
                f"Os parâmetros configurados para o modelo "
                f"{configuration.key!r} não correspondem ao "
                f"construtor de {configuration.adapter!r}: {error}. "
                f"Parâmetros declarados pelo adaptador: {accepted}."
            ) from error

        return arguments

    def validate(
        self,
        model: str | ModelConfiguration,
        *,
        parameter_overrides: Mapping[str, Any] | None = None,
        validate_declared_files: bool = True,
        validate_adapter_files: bool = True,
    ) -> dict[str, Any]:
        """Executa a validação completa sem carregar os pesos."""

        configuration = self._resolve_configuration(model)
        adapter_class = self.resolve_adapter_class(
            configuration
        )

        declared_files: tuple[Path, ...] = tuple()
        if validate_declared_files:
            declared_files = self.validate_files(
                configuration
            )

        constructor_arguments = (
            self.build_constructor_arguments(
                configuration,
                parameter_overrides=parameter_overrides,
                adapter_class=adapter_class,
            )
        )

        instance = self._instantiate(
            configuration,
            adapter_class,
            constructor_arguments,
        )

        try:
            if validate_adapter_files:
                instance.validate_model_files()

            self._validate_instance(
                configuration,
                instance,
                constructor_arguments,
            )
        finally:
            if instance.is_loaded:
                instance.unload()

        return {
            "model_key": configuration.key,
            "model_name": configuration.model_name,
            "adapter": configuration.adapter,
            "adapter_class": adapter_class.__name__,
            "model_dir": str(configuration.model_dir),
            "declared_files": [
                str(path)
                for path in declared_files
            ],
            "parameters": copy.deepcopy(
                configuration.parameters
            ),
            "requested_device": instance.requested_device,
            "resolved_device": instance.device_type,
            "device_name": instance.device_name,
            "valid": True,
        }

    def validate_all(
        self,
        *,
        validate_declared_files: bool = True,
        validate_adapter_files: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        """Valida todos os modelos registrados."""

        return tuple(
            self.validate(
                configuration,
                validate_declared_files=(
                    validate_declared_files
                ),
                validate_adapter_files=(
                    validate_adapter_files
                ),
            )
            for configuration in self.configurations
        )

    def create(
        self,
        model: str | ModelConfiguration,
        *,
        parameter_overrides: Mapping[str, Any] | None = None,
        validate_declared_files: bool = True,
        validate_adapter_files: bool = True,
        load: bool = False,
        replace_existing: bool = False,
    ) -> RegisteredModel:
        """Cria uma instância e opcionalmente carrega seus pesos."""

        configuration = self._resolve_configuration(model)

        existing = self._instances.get(configuration.key)
        if existing is not None and not replace_existing:
            if parameter_overrides:
                raise ModelInstantiationError(
                    f"O modelo {configuration.key!r} já possui uma "
                    "instância registrada. Para aplicar parâmetros "
                    "diferentes, use replace_existing=True."
                )

            if load and not existing.is_loaded:
                existing.load()

            return existing

        if existing is not None:
            existing.unload()
            del self._instances[configuration.key]

        adapter_class = self.resolve_adapter_class(
            configuration
        )

        if validate_declared_files:
            self.validate_files(configuration)

        constructor_arguments = (
            self.build_constructor_arguments(
                configuration,
                parameter_overrides=parameter_overrides,
                adapter_class=adapter_class,
            )
        )

        instance = self._instantiate(
            configuration,
            adapter_class,
            constructor_arguments,
        )

        try:
            if validate_adapter_files:
                instance.validate_model_files()

            self._validate_instance(
                configuration,
                instance,
                constructor_arguments,
            )

            if load:
                instance.load()
        except Exception:
            if instance.is_loaded:
                instance.unload()
            raise

        registered = RegisteredModel(
            configuration=configuration,
            adapter_class=adapter_class,
            instance=instance,
            constructor_arguments=constructor_arguments,
        )

        self._instances[configuration.key] = registered
        return registered

    def get_instance(
        self,
        key: str,
    ) -> RegisteredModel:
        """Retorna uma instância já criada."""

        normalized_key = str(key).strip()

        try:
            return self._instances[normalized_key]
        except KeyError as error:
            raise ModelNotRegisteredError(
                f"O modelo {normalized_key!r} está configurado, "
                "mas ainda não foi instanciado."
            ) from error

    def unload(
        self,
        key: str,
        *,
        remove_instance: bool = False,
    ) -> None:
        """Libera um modelo já criado."""

        registered = self.get_instance(key)
        registered.unload()

        if remove_instance:
            del self._instances[registered.key]

    def unload_all(
        self,
        *,
        remove_instances: bool = False,
    ) -> None:
        """Libera todos os modelos criados."""

        for key in tuple(self._instances):
            registered = self._instances[key]
            registered.unload()

            if remove_instances:
                del self._instances[key]

    def metadata(self) -> dict[str, Any]:
        """Resume configurações e estado atual do registry."""

        return {
            "model_count": len(self),
            "model_keys": list(self.keys),
            "instantiated_keys": list(
                self.instantiated_keys
            ),
            "models": [
                {
                    "model_key": configuration.key,
                    "model_name": (
                        configuration.model_name
                    ),
                    "display_name": (
                        configuration.display_name
                    ),
                    "enabled": configuration.enabled,
                    "order": configuration.order,
                    "adapter": configuration.adapter,
                    "model_dir": str(
                        configuration.model_dir
                    ),
                    "parameters": copy.deepcopy(
                        configuration.parameters
                    ),
                    "is_instantiated": (
                        configuration.key
                        in self._instances
                    ),
                    "is_loaded": bool(
                        self._instances.get(
                            configuration.key
                        )
                        and self._instances[
                            configuration.key
                        ].is_loaded
                    ),
                }
                for configuration in self.configurations
            ],
        }

    def _resolve_configuration(
        self,
        model: str | ModelConfiguration,
    ) -> ModelConfiguration:
        if isinstance(model, ModelConfiguration):
            registered = self._configurations.get(
                model.key
            )

            if registered is None:
                raise ModelNotRegisteredError(
                    f"O modelo {model.key!r} não pertence a este "
                    "registry."
                )

            return registered

        return self.get_configuration(str(model))

    @staticmethod
    def _split_adapter_path(
        configuration: ModelConfiguration,
    ) -> tuple[str, str]:
        adapter_path = configuration.adapter.strip()

        if "." not in adapter_path:
            raise ModelAdapterImportError(
                f"Caminho de adaptador inválido no modelo "
                f"{configuration.key!r}: {adapter_path!r}."
            )

        module_name, class_name = adapter_path.rsplit(
            ".",
            1,
        )

        if not module_name or not class_name:
            raise ModelAdapterImportError(
                f"Caminho de adaptador inválido no modelo "
                f"{configuration.key!r}: {adapter_path!r}."
            )

        return module_name, class_name

    @staticmethod
    def _get_constructor_signature(
        adapter_class: type[BaseSentimentModel],
    ) -> inspect.Signature:
        try:
            return inspect.signature(adapter_class)
        except (TypeError, ValueError) as error:
            raise ModelAdapterContractError(
                f"Não foi possível inspecionar o construtor de "
                f"{adapter_class.__module__}."
                f"{adapter_class.__name__}: {error}"
            ) from error

    @staticmethod
    def _instantiate(
        configuration: ModelConfiguration,
        adapter_class: type[BaseSentimentModel],
        constructor_arguments: Mapping[str, Any],
    ) -> BaseSentimentModel:
        try:
            instance = adapter_class(
                **dict(constructor_arguments)
            )
        except Exception as error:
            raise ModelInstantiationError(
                f"Não foi possível instanciar o modelo "
                f"{configuration.key!r} usando "
                f"{configuration.adapter!r}: {error}"
            ) from error

        if not isinstance(instance, BaseSentimentModel):
            raise ModelAdapterContractError(
                f"O adaptador {configuration.adapter!r} retornou "
                "uma instância incompatível com "
                "BaseSentimentModel."
            )

        return instance

    @staticmethod
    def _validate_instance(
        configuration: ModelConfiguration,
        instance: BaseSentimentModel,
        constructor_arguments: Mapping[str, Any],
    ) -> None:
        """Confirma que o construtor preservou os valores efetivos."""

        expected_model_name = str(
            constructor_arguments["model_name"]
        )
        expected_model_dir = Path(
            constructor_arguments["model_dir"]
        ).resolve()

        if instance.model_name != expected_model_name:
            raise ModelAdapterContractError(
                f"O adaptador do modelo "
                f"{configuration.key!r} alterou model_name. "
                f"Esperado: {expected_model_name!r}; "
                f"recebido: {instance.model_name!r}."
            )

        instance_dir = instance.model_dir.resolve()

        if instance_dir != expected_model_dir:
            raise ModelAdapterContractError(
                f"O adaptador do modelo "
                f"{configuration.key!r} alterou model_dir. "
                f"Esperado: {expected_model_dir}; "
                f"recebido: {instance_dir}."
            )

        expected_batch_size = int(
            constructor_arguments["batch_size"]
        )
        expected_max_length = int(
            constructor_arguments["max_length"]
        )
        expected_device = str(
            constructor_arguments["device"]
        ).lower()

        if instance.batch_size != expected_batch_size:
            raise ModelAdapterContractError(
                f"O adaptador do modelo "
                f"{configuration.key!r} alterou batch_size. "
                f"Esperado: {expected_batch_size}; "
                f"recebido: {instance.batch_size}."
            )

        if instance.max_length != expected_max_length:
            raise ModelAdapterContractError(
                f"O adaptador do modelo "
                f"{configuration.key!r} alterou max_length. "
                f"Esperado: {expected_max_length}; "
                f"recebido: {instance.max_length}."
            )

        if instance.requested_device != expected_device:
            raise ModelAdapterContractError(
                f"O adaptador do modelo "
                f"{configuration.key!r} alterou device. "
                f"Esperado: {expected_device!r}; "
                f"recebido: "
                f"{instance.requested_device!r}."
            )


def create_model_registry(
    configuration: ResolvedConfiguration
    | Iterable[ModelConfiguration],
) -> ModelRegistry:
    """Cria um registry a partir da configuração resolvida ou de modelos."""

    if isinstance(
        configuration,
        ResolvedConfiguration,
    ):
        return ModelRegistry.from_resolved_configuration(
            configuration
        )

    return ModelRegistry(configuration)


__all__ = [
    "ModelAdapterContractError",
    "ModelAdapterImportError",
    "ModelFileValidationError",
    "ModelInstantiationError",
    "ModelNotRegisteredError",
    "ModelRegistry",
    "ModelRegistryError",
    "RegisteredModel",
    "create_model",
    "create_model_registry",
]