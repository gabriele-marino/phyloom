from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, overload

if TYPE_CHECKING:
    from phyloom.types import Context

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class Contextualizable(Protocol[T_co]):
    """Protocol for a configuration value resolved against a context."""

    def contextualize(self, context: Context) -> T_co:
        """Resolve the configuration value from materialized context values."""
        ...


@overload
def contextualize_optional(cfg: None, context: Context) -> None: ...
@overload
def contextualize_optional(cfg: Contextualizable[T], context: Context) -> T: ...
def contextualize_optional(
    cfg: Contextualizable[T] | None, context: Context
) -> T | None:
    """Resolve ``cfg`` against ``context`` while preserving ``None``."""
    return None if cfg is None else cfg.contextualize(context)
