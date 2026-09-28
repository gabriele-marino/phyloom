"""Configuration of the age-dependent branching model."""

# This is the module named by the ``phyloom.plugins`` entry point in
# ``pyproject.toml``. Importing it runs the registration decorator below, and
# from then on YAML configurations can select the model with ``spec: adb``.

from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.configs import MODEL_REGISTRY, ModelCfgBase
from phyloom.configs.roots import StrCfg
from phyloom_adb.expressions import ChildStatesExpression, FloatStateExpression
from phyloom_adb.model import ADBModel

if TYPE_CHECKING:
    from phyloom.types import Context


@MODEL_REGISTRY.register("adb")
class ADBModelCfg(ModelCfgBase):
    """Configuration for :class:`~phyloom_adb.model.ADBModel`."""

    # Each field declares one key of the YAML ``model`` block and its type:
    # ``init_state`` is a context-dependent string with ``{name}``
    # placeholders, and the three expressions become callables of
    # ``(model, state)``. There are no ``events`` or ``schedule`` fields,
    # unlike the built-in models: the three expressions describe the whole process.
    init_state: StrCfg
    lifetime_func: FloatStateExpression
    death_prob: FloatStateExpression
    get_child_states: ChildStatesExpression | None = None

    # ``contextualize`` binds the sample's context once and creates the
    # runtime model. The runner calls it once per trial, so it must
    # always build a new model.
    def contextualize(self, context: Context) -> ADBModel:
        """Build a new model for a sample's context."""
        return ADBModel(
            init_state=self.init_state.contextualize(context),
            lifetime_func=self.lifetime_func.contextualize(context),
            death_prob=self.death_prob.contextualize(context),
            get_child_states=(
                self.get_child_states.contextualize(context)
                if self.get_child_states is not None
                else None
            ),
        )
