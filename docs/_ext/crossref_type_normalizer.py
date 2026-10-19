"""Normalize Sphinx cross-reference targets for known types and API objects."""

from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from phyloom import types

_ROLES: dict[str, str] = {
    "pathlib.Path": "class",
    "pandas.DataFrame": "class",
    "phyloom.configs.core.ModelCfg": "type",
    "phyloom.configs.hazards.HazardCfg": "type",
    "random.Random": "class",
    "typing.Any": "obj",
    "typing.Literal": "obj",
    "typing.Self": "obj",
    "typing.TypeGuard": "obj",
}
_ROLES.update(
    {
        f"collections.abc.{name}": "class"
        for name in ["Iterator", "Mapping", "Sequence", "Iterable", "Callable"]
    }
)
_ROLES.update({f"phyloom.types.{alias}": "type" for alias in types.__all__})
REFS = {
    "pd.DataFrame" if ref == "pandas.DataFrame" else ref.rsplit(".", 1)[-1]: ref
    for ref in _ROLES
}


def crossref_type_normalizer(_app: Sphinx, doctree: nodes.document) -> None:
    for signature in doctree.findall(addnodes.desc_signature):
        for xref in signature.findall(addnodes.pending_xref):
            reftarget = xref["reftarget"]
            if reftarget in REFS:
                ref = REFS[reftarget]
                xref["reftarget"] = ref
                xref["reftype"] = _ROLES[ref]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("doctree-read", crossref_type_normalizer)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
