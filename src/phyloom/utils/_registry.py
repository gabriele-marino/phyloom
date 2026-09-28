from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeGuard

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)
RegisteredT = TypeVar("RegisteredT", bound=type[BaseModel])


def _is_dictionary(x: object) -> TypeGuard[dict[object, object]]:
    return isinstance(x, dict)


class Registry(Generic[BaseModelT]):
    """Registry for polymorphic Pydantic configuration models.

    A registry maps string discriminator keys to subclasses of a
    :class:`pydantic.BaseModel`. It can load a mapping into the corresponding
    registered class, or expose the same behavior as a
    :class:`pydantic.BeforeValidator` through :attr:`validator` for an
    annotated configuration field.

    Args:
        name: Human-readable name used in registry errors.
        base_type: Base model class that every registered class must extend.
        discriminator: Input field containing the registration key.

    Examples:
        Register a concrete Pydantic model under a discriminator key, retrieve
        the registered class, and load configured model instances.

        >>> from typing import Annotated
        >>> from pydantic import BaseModel
        >>> from phyloom.utils import Registry
        >>> class Plugin(BaseModel):
        ...     kind: str = "plugin"
        >>> registry = Registry("plugin", Plugin, "name")
        >>> @registry.register("demo")
        ... class DemoPlugin(Plugin):
        ...     data: int = 1
        >>> registry.get("demo") is DemoPlugin
        True
        >>> loaded = registry.load({"name": "demo", "data": 3})
        >>> type(loaded) is DemoPlugin
        True
        >>> loaded.kind, loaded.data
        ('plugin', 3)
        >>> existing = DemoPlugin(data=2)
        >>> registry.load(existing) is existing
        True

        Use the validator in an annotated Pydantic field to load registered
        models during validation.

        >>> class Config(BaseModel):
        ...     plugin: Annotated[Plugin, registry.validator]
        >>> configured = Config.model_validate(
        ...     {"plugin": {"name": "demo", "data": 4}}
        ... )
        >>> type(configured.plugin) is DemoPlugin
        True
        >>> configured.plugin.kind, configured.plugin.data
        ('plugin', 4)
    """

    def __init__(
        self, name: str, base_type: type[BaseModelT], discriminator: str = "spec"
    ):
        self._name = name
        self._base_type = base_type
        self._discriminator = discriminator
        self._registry: dict[str, type[BaseModelT]] = {}

    def register(self, key: str) -> Callable[[RegisteredT], RegisteredT]:
        """Return a decorator that registers a model class under ``key``.

        The decorated class must inherit from the registry's base type, and
        each key may be registered only once.
        """

        def decorator(cls: RegisteredT) -> RegisteredT:
            if not issubclass(cls, self._base_type):
                raise TypeError(
                    f"Cannot register {cls.__name__} in {self._name} registry: it must "
                    f"be a subclass of {self._base_type.__name__}."
                )
            if key in self._registry:
                existing = self._registry[key]
                raise RuntimeError(
                    f"Cannot register {cls.__name__} in {self._name} registry: key '{key}' "
                    f"already maps to {existing.__name__}."
                )
            self._registry[key] = cls
            return cls

        return decorator

    def keys(self) -> list[str]:
        """Return the registered discriminator keys in registration order."""
        return list(self._registry.keys())

    def get(self, key: str) -> type[BaseModelT]:
        """Return the registered model class for ``key``."""
        if key not in self._registry:
            raise ValueError(
                f"Unknown key '{key}' in {self._name} registry. Available keys: {self.keys()}."
            )
        return self._registry[key]

    def load(self, value: object) -> BaseModelT:
        """Load a registered model from a mapping or return an existing one.

        For mappings, the discriminator field selects the concrete class and
        is removed before Pydantic validates the remaining fields. Existing
        instances of the registry's base type are returned unchanged.
        """
        if isinstance(value, self._base_type):
            return value

        if not _is_dictionary(value):
            raise ValueError(
                f"Cannot load from {self._name} registry: expected a dict or an instance of "
                f"{self._base_type.__name__}, got {type(value).__name__}."
            )

        if self._discriminator not in value:
            raise ValueError(
                f"Cannot load from {self._name} registry: missing discriminator field '{self._discriminator}'."
            )
        key = value[self._discriminator]
        if not isinstance(key, str):
            raise ValueError(  # noqa: TRY004
                f"Cannot load from {self._name} registry: discriminator field "
                f"'{self._discriminator}' must be a string, got {type(key).__name__}."
            )
        data = {k: v for k, v in value.items() if k != self._discriminator}

        cls = self.get(key)
        return cls.model_validate(data)

    @property
    def validator(self) -> BeforeValidator:
        """Pydantic validator that loads a registered model from a mapping or returns an existing instance, backed by :meth:`load`."""
        return BeforeValidator(self.load)

    def __len__(self) -> int:
        """Return the number of registered model classes."""
        return len(self._registry)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name={self._name!r}, "
            f"base_type={self._base_type.__name__!r}, keys={self.keys()!r})"
        )
