"""Clean up autodoc output for Pydantic models."""

from typing import TypeGuard

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options
from sphinx.util.typing import ExtensionMetadata, restify


def _is_pydantic_model(obj: object) -> TypeGuard[type[BaseModel]]:
    return isinstance(obj, type) and issubclass(obj, BaseModel)


def _process_pydantic_model_signature(
    app: Sphinx,
    what: str,
    _name: str,
    obj: object,
    _options: Options,
    _signature: str | None,
    _return_annotation: str | None,
) -> tuple[str, None] | None:
    if not _is_pydantic_model(obj) or not obj.model_fields:
        return None

    def get_default(field: FieldInfo) -> str:
        return (
            ""
            if field.is_required()
            else f" = {field.default!r}"
            if field.default_factory is None
            else f" = {field.default_factory.__name__}()"
        )

    annotations = {
        name: annotation
        for cls in reversed(obj.__mro__)
        for name, annotation in getattr(cls, "__annotations__", {}).items()
    }
    parts = [
        f"{name}: {annotations[name]}{get_default(field)}"
        for name, field in obj.model_fields.items()
    ]
    return f"(*, {', '.join(parts)})", None


def _format_pydantic_base(base: object) -> str | None:
    if not _is_pydantic_model(base):
        return None

    metadata = getattr(base, "__pydantic_generic_metadata__", {})
    origin = metadata.get("origin")
    arguments = metadata.get("args", ())
    if not isinstance(origin, type) or not arguments:
        return None

    rendered_arguments = ", ".join(
        restify(argument, "smart") for argument in arguments
    )
    return f"{restify(origin, 'smart')}\\ [{rendered_arguments}]"


def _process_config_model_bases(
    _app: Sphinx,
    _name: str,
    _obj: object,
    _options: Options,
    bases: list[object],
) -> None:
    bases[:] = [
        formatted_base if (formatted_base := _format_pydantic_base(base)) else base
        for base in bases
    ]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("autodoc-process-signature", _process_pydantic_model_signature)
    app.connect("autodoc-process-bases", _process_config_model_bases)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
