from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from pydantic import ConfigDict, RootModel

if TYPE_CHECKING:
    from pathlib import Path

    from phyloom.types import Context


class PostCommandCfg(RootModel[str]):
    """Configuration for a context-interpolated shell command run on the output directory of a sample.

    Interpolation is performed using standard Python string formatting
    (:meth:`str.format`), where ``{name}`` placeholders matching context
    variables are replaced with their corresponding values, and the
    ``{output_dir}`` placeholder with the sample's output directory. The
    command runs through the system shell and is not sandboxed, so
    configuration input must be trusted.
    """

    model_config = ConfigDict(frozen=True)

    root: str

    def run(self, context: Context, output_dir: Path) -> None:
        """Interpolate the command from materialized context values and ``output_dir``, then run it."""
        command = self.root.format(**{**context, "output_dir": output_dir})
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=False
        )
        if result.returncode:
            raise RuntimeError(
                f"Shell command {command!r} failed with exit status "
                f"{result.returncode}: {result.stderr.strip()}"
            )
