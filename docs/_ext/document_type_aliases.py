"""Document ``TypeAlias`` declarations as Sphinx types."""

from typing import TypeAlias

from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.ext.autodoc import (
    ClassDocumenter,
    DataDocumenter,
    Documenter,
    ModuleDocumenter,
)
from sphinx.util.typing import ExtensionMetadata


def _is_type_alias(module: object, name: str) -> bool:
    annotation = getattr(module, "__annotations__", {}).get(name)
    return annotation in (TypeAlias, "TypeAlias")


class TypeAliasDocumenter(DataDocumenter):
    objtype = "type"
    priority = ClassDocumenter.priority + 1

    @classmethod
    def can_document_member(
        cls,
        member: object,
        membername: str,
        isattr: bool,
        parent: object,
    ) -> bool:
        return isinstance(parent, ModuleDocumenter) and _is_type_alias(
            parent.object, membername
        )

    def add_directive_header(self, sig: str) -> None:
        Documenter.add_directive_header(self, sig)

    def update_content(self, more_content: StringList) -> None: ...


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_autodocumenter(TypeAliasDocumenter)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
