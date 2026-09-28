"""Skip undocumented project methods and properties in Sphinx autodoc."""

import inspect

from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options
from sphinx.util.typing import ExtensionMetadata


def _skip_undocumented_members(
    _app: Sphinx,
    _what: str,
    name: str,
    obj: object,
    _skip: bool,
    _options: Options,
) -> bool | None:
    if isinstance(obj, property):
        source = obj.fget
    elif inspect.isroutine(obj):
        source = obj
    else:
        return None

    if source is None:
        return None

    doc = getattr(obj, "__doc__", None)
    module = getattr(source, "__module__", None)
    has_doc = isinstance(doc, str) and bool(doc.strip())
    is_project_object = isinstance(module, str) and module.startswith("phyloom.")
    return not has_doc if is_project_object else None


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("autodoc-skip-member", _skip_undocumented_members)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
