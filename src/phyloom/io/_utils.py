from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from phyloom.types import PathLike


def iter_stripped_lines(filepath: PathLike) -> Iterator[str]:
    with open(filepath, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield line.strip()
