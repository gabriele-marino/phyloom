"""Configuration and execution entrypoint for the dataset-generation pipeline."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter
from typing import TYPE_CHECKING

import pandas as pd
from numpy.random import default_rng
from pydantic import BaseModel, ConfigDict

from phyloom.configs.core import ModelCfg
from phyloom.configs.roots import (
    ContextCfg,
    FloatCfg,
    ModelActionCfg,
    ModelExpressionCfg,
    ModelPredicateCfg,
    OutputHookCfg,
    PostCommandCfg,
)
from phyloom.configs.utils import contextualize_optional
from phyloom.simulator.utils import run_simulations

if TYPE_CHECKING:
    from phyloom.types import Context, SampleID, Seed

DATA_DIRNAME = "data"
METADATA_FILENAME = "metadata.csv"


class Runner(BaseModel):
    """Entry point for the dataset-generation pipeline.

    For every sample, the runner materializes sample-specific values from the
    context priors, builds and advances a model, evaluates the stopping and
    acceptance criteria, and records the accepted sample. An unsplit run
    writes its output to ``output_dir``, and a split run writes each split to
    ``output_dir/<split>`` with the same layout:

    * ``data/<sample_id>/``: the files written by ``output_hooks`` and
      ``post_commands`` for each accepted sample;
    * ``metadata.csv``: one row per sample, with its materialized context values,
      its ``logs``, the number of rejected trials (``n_rejections``), and the
      wall-clock run time (``total_time``);
    * ``timed_out_contexts.csv`` and ``max_rejections_exceeded_contexts.csv``:
      the materialized context values abandoned after a timeout or after too many
      rejections, if any.

    Args:
        output_dir: Root directory for generated data. An unsplit run writes
            its output directly here; split runs create one subdirectory per split.
        n_samples: Number of samples, or a mapping from split names to sample
            counts. Mapping keys name the output split directories.
        n_jobs: Number of worker processes passed to :func:`joblib.Parallel`.
            ``-1`` uses all available CPUs.
        seed: Optional seed for the random number generator used to derive per-sample
            seeds. If ``None``, a non-deterministic seed source is used.
        context: Priors of the parameters, as named random draws, constants,
            and derived expressions. Sample-specific values are drawn from these
            priors, and can be used in the model configuration, stopping and
            acceptance criteria, logs, hooks and post-commands. Rejected trials are
            rerun with the same values; values whose trials time out or exceed the
            maximum rejection threshold are replaced by a new draw from the priors.
            The values of each accepted sample are recorded in ``metadata.csv``.
        model: Registered model configuration to materialize for each trial.
        max_time: Optional inclusive upper bound on simulated time.
        stop_criterion: Optional model predicate evaluated after each
            successful simulation step. A true result ends the trial.
        acceptance_criterion: Optional model predicate evaluated after a
            trial. A false result rejects the trial and starts another one.
        stop_hook: Optional model action evaluated after an accepted trial
            stops.
        max_rejections: Maximum number of rejected trials permitted for one
            context. When the limit is exceeded, the context is replaced and
            recorded in ``max_rejections_exceeded_contexts.csv`` in the
            relevant output directory.
        timeout: Optional wall-clock limit in seconds for one trial. A timed-out
            context is replaced and recorded in
            ``timed_out_contexts.csv`` in the relevant output directory.
        logs: Mapping from metadata column names to model expressions evaluated
            after an accepted trial. Their results become columns in
            ``metadata.csv``.
        output_hooks: Output-hook statements run in order after each accepted
            trial. They can write files to the sample's output directory.
        post_commands: Shell commands run in order, last, after the output hooks
            of each accepted trial, such as external simulators of sequence or
            trait evolution that read the files written by the hooks.
    """

    model_config = ConfigDict(extra="forbid")

    output_dir: str = "phyloom-outputs"
    n_samples: int | dict[str, int] = 1
    n_jobs: int = -1
    seed: int | None = None
    context: ContextCfg = ContextCfg()

    model: ModelCfg
    max_time: FloatCfg | None = None
    stop_criterion: ModelPredicateCfg | None = None
    acceptance_criterion: ModelPredicateCfg | None = None
    stop_hook: ModelActionCfg | None = None
    max_rejections: int | None = None
    timeout: float | None = None
    logs: dict[str, ModelExpressionCfg] = {}

    output_hooks: tuple[OutputHookCfg, ...]
    post_commands: tuple[PostCommandCfg, ...] = ()

    def _generate_sample(
        self, sample_id: SampleID, seed: Seed, *, data_dir: Path
    ) -> dict[str, object]:
        timed_out_contexts: list[Context] = []
        max_rejections_exceeded_contexts: list[Context] = []
        rng = Random(seed)
        run_start = perf_counter()

        while True:
            context = self.context.materialize(default_rng(rng.getrandbits(32)))
            max_time = contextualize_optional(self.max_time, context)
            if max_time is not None and max_time <= 0:
                raise ValueError(
                    f"Maximum time must be positive (got max_time={max_time})"
                )
            stop_criterion = contextualize_optional(self.stop_criterion, context)
            acceptance_criterion = contextualize_optional(
                self.acceptance_criterion, context
            )
            stop_hook = contextualize_optional(self.stop_hook, context)

            n_rejections = 0
            while True:
                model = self.model.contextualize(context)
                model.rng.seed(rng.getrandbits(32))
                trial_start = perf_counter()
                timed_out = False

                while model.step(max_time):
                    if stop_criterion is not None and stop_criterion(model):
                        break
                    if (
                        self.timeout is not None
                        and perf_counter() - trial_start > self.timeout
                    ):
                        timed_out = True
                        break

                if timed_out:
                    timed_out_contexts.append(context)
                    break

                if acceptance_criterion is not None and not acceptance_criterion(model):
                    n_rejections += 1
                    if (
                        self.max_rejections is not None
                        and n_rejections > self.max_rejections
                    ):
                        max_rejections_exceeded_contexts.append(context)
                        break
                    continue

                if stop_hook is not None:
                    stop_hook(model)

                metadata: dict[str, object] = {
                    "n_rejections": n_rejections,
                    "total_time": perf_counter() - run_start,
                }
                for key, value in self.logs.items():
                    metadata[key] = value.contextualize(context)(model)
                output_dir = data_dir / str(sample_id)
                output_dir.mkdir(parents=True)
                for hook in self.output_hooks:
                    hook.contextualize(context)(model, output_dir)
                for command in self.post_commands:
                    command.run(context, output_dir)

                return {
                    **context,
                    **metadata,
                    "timed_out_contexts": timed_out_contexts,
                    "max_rejections_exceeded_contexts": max_rejections_exceeded_contexts,
                }

    def _generate_split(self, n_samples: int, output_dir: Path, seed: Seed):
        if output_dir.exists():
            print(f"Output directory {output_dir} already exists. Skipping.")
            return

        output_dir.mkdir(parents=True)
        data_dir = output_dir / DATA_DIRNAME
        df = run_simulations(
            n_samples,
            partial(self._generate_sample, data_dir=data_dir),
            seed=seed,
            n_jobs=self.n_jobs,
        )

        for name in ["timed_out_contexts", "max_rejections_exceeded_contexts"]:
            meta_df = pd.DataFrame([d for row in df[name] for d in row])
            if not meta_df.empty:
                meta_df.to_csv(output_dir / f"{name}.csv", index=False)
            df = df.drop(columns=[name])

        df.to_csv(output_dir / METADATA_FILENAME, index=False)

    def run(self):
        """Generate samples according to the configuration.

        Existing split directories are skipped, allowing completed splits to
        be retained when a multi-split run is resumed.
        """
        rng = Random(self.seed)
        output_dir = Path(self.output_dir)
        if isinstance(self.n_samples, dict):
            for split, n_samples in self.n_samples.items():
                self._generate_split(n_samples, output_dir / split, rng.getrandbits(32))
        else:
            self._generate_split(self.n_samples, output_dir, rng.getrandbits(32))
