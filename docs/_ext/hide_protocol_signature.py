"""Hide unusable constructor signatures generated for protocols."""

from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options
from sphinx.util.typing import ExtensionMetadata


def _hide_protocol_signature(
    _app: Sphinx,
    what: str,
    _name: str,
    obj: object,
    _options: Options,
    _signature: str | None,
    return_annotation: str | None,
) -> tuple[str | None, str | None] | None:
    if what == "class" and getattr(obj, "_is_protocol", False):
        return "", return_annotation
    return None


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("autodoc-process-signature", _hide_protocol_signature)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
