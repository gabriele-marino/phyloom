"""Hide ``object`` and private classes from the bases shown by autodoc.

A private base is replaced by its own public bases, and inheritance rows left
empty are removed.
"""

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options
from sphinx.util.typing import ExtensionMetadata


def _hide_object_base(
    _app: Sphinx,
    _name: str,
    _obj: object,
    _options: Options,
    bases: list[object],
) -> None:
    bases[:] = [base for base in _public_bases(bases) if base is not object]


def _public_bases(bases: list[object]) -> list[object]:
    public: list[object] = []
    for base in bases:
        if isinstance(base, type) and base.__name__.startswith("_"):
            public.extend(_public_bases(list(base.__bases__)))
        else:
            public.append(base)
    return public


def _remove_empty_bases(
    _app: Sphinx,
    doctree: nodes.document,
    _docname: str,
) -> None:
    for paragraph in list(doctree.findall(nodes.paragraph)):
        if paragraph.astext() == "Bases:":
            paragraph.parent.remove(paragraph)


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("autodoc-process-bases", _hide_object_base)
    app.connect("doctree-resolved", _remove_empty_bases)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
