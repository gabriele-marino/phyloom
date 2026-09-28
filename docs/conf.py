import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "_ext"))

from crossref_type_normalizer import REFS

project = "phyloom"
author = "Gabriele Marino"

extensions = [
    "myst_parser",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
]
extensions.extend(
    [
        "crossref_type_normalizer",
        "document_type_aliases",
        "hide_object_inheritance",
        "hide_protocol_signature",
        "pydantic_model_signatures",
        "skip_pydantic_model_config",
        "skip_undocumented_members",
    ]
)
myst_enable_extensions = [
    "dollarmath",
]

intersphinx_mapping = {
    "joblib": ("https://joblib.readthedocs.io/en/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "pydantic": ("https://pydantic.dev/docs/validation/latest/", None),
    "python": ("https://docs.python.org/3", None),
}

html_show_sourcelink = False
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["hide_home_title.css"]

autodoc_default_options = {"show-inheritance": True}
autodoc_member_order = "bysource"
autodoc_type_aliases: dict[str, str] = {ref: f"~{ref}" for ref in REFS}

copybutton_prompt_text = r">>> |\.\.\. "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = True
