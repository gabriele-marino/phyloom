"""Skip Pydantic model configuration attributes in Sphinx autodoc."""

from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options
from sphinx.util.typing import ExtensionMetadata


def _skip_model_config(
    _app: Sphinx,
    _what: str,
    name: str,
    _obj: object,
    _skip: bool,
    _options: Options,
) -> bool | None:
    if name == "model_config":
        return True
    return None


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("autodoc-skip-member", _skip_model_config)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
