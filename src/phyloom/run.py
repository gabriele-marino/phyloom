from __future__ import annotations

import os
import sys
from glob import glob
from importlib import import_module
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from pydantic import ValidationError
from yaml import YAMLError, safe_load

from phyloom.configs.runner import Runner

if TYPE_CHECKING:
    from phyloom.types import PathLike

PLUGIN_ENTRY_POINT_GROUP = "phyloom.plugins"


def _load_plugins():
    for entry_point in entry_points(group=PLUGIN_ENTRY_POINT_GROUP):
        import_module(entry_point.value)


def _format_validation_error(e: ValidationError) -> str:
    formatted_errors = [
        f"- {'.'.join(str(loc) for loc in err['loc'])}: {err['msg']} ({err['type']})"
        for err in e.errors()
    ]
    return "\n".join(formatted_errors)


def _run_from_config_file(config_file: PathLike):
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            try:
                config = safe_load(f)
            except YAMLError as e:
                print(f"❌ Failed to parse {config_file}: {e}")
                sys.exit(-1)

            try:
                runner = Runner.model_validate(config)
            except ValidationError as e:
                print("❌ Invalid configuration:")
                print(_format_validation_error(e))
                sys.exit(-1)
    except OSError as e:
        print(f"❌ Failed to load {config_file}: {e}")
        sys.exit(-1)
    runner.run()


def run(config_path: PathLike):
    """Run a simulation from a configuration file or directory of configuration files."""
    _load_plugins()
    if os.path.isdir(config_path):
        for config_file in glob(os.path.join(config_path, "**/*.yaml"), recursive=True):
            _run_from_config_file(config_file)
    else:
        _run_from_config_file(config_path)
