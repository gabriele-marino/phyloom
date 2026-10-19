from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ConfigDict, RootModel

if TYPE_CHECKING:
    from phyloom.types import Context


class StrCfg(RootModel[str]):
    """Configuration for a context-interpolated string.

    Interpolation is performed using standard Python string formatting
    (:meth:`str.format`), where ``{name}`` placeholders matching context
    variables are replaced with their corresponding values.
    """

    model_config = ConfigDict(frozen=True)

    root: str

    def contextualize(self, context: Context) -> str:
        """Interpolate the string from materialized context values."""
        return self.root.format(**context)


class StrPairCfg(RootModel[tuple[StrCfg, StrCfg]]):
    """Configuration for a pair of context-interpolated strings."""

    root: tuple[StrCfg, StrCfg]

    def contextualize(self, context: Context) -> tuple[str, str]:
        """Interpolate both strings from materialized context values."""
        str1, str2 = self.root
        return str1.contextualize(context), str2.contextualize(context)
