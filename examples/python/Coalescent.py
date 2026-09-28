"""Kingman coalescent.

The genealogy of lineages sampled from a single population of constant size.
The simulation runs backward in time, from the samples at the present until
they have all merged into one common ancestor. The initial lineages are the
samples, and the whole genealogy is the output.

Run it from the repository root with `python examples/python/Coalescent.py`.
`examples/yaml/Coalescent.yaml` builds the same model as a YAML configuration
and explains its specifics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.coalescent import Coalesce, CoalescentModel
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

# Dataset settings.
OUTPUT_DIR = Path("outputs/Coalescent-python")
N_SAMPLES = {"train": 10, "val": 2, "test": 2}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    """The parameters of one sample."""

    n_tips: int
    effective_population_size: int
    coalescence_rate: float


def draw_context(rng: np.random.Generator) -> Context:
    """Draw the parameters of one sample."""
    n_tips = int(rng.integers(low=8, high=13))
    effective_population_size = 100
    return Context(
        n_tips=n_tips,
        effective_population_size=effective_population_size,
        coalescence_rate=1 / (2 * effective_population_size),
    )


def build_model(ctx: Context) -> CoalescentModel:
    """Build a fresh model for one trial."""
    return CoalescentModel(
        init_population={"A": ctx.n_tips},
        events=[
            Event(
                Coalesce(current_states=("A", "A"), ancestral_state="A"),
                ConstantHazard(ctx.coalescence_rate),
            ),
        ],
    )


def should_stop(model: CoalescentModel, ctx: Context) -> bool:
    """The stop criterion, checked after every step."""
    return model.count_current_lineages() == 1


def write_outputs(model: CoalescentModel, sample_dir: Path) -> None:
    """Write the files of an accepted trial to the sample's folder."""
    model.history().dump(sample_dir / "genealogy.nwk")


def simulate(sample_id: int, seed: int, *, data_dir: Path) -> dict[str, object]:
    """Generate one accepted sample and return its `metadata.csv` row.

    `run_simulations` calls this once per sample, with the sample id and a
    seed derived from the split's seed. There is no acceptance criterion, so
    the first trial is always accepted.
    """
    # The sample's random stream gives one seed for the context draws, then one
    # seed for the model of the trial.
    rng = Random(seed)
    start = perf_counter()
    ctx = draw_context(np.random.default_rng(rng.getrandbits(32)))

    model = build_model(ctx)
    model.rng.seed(rng.getrandbits(32))
    # step() applies the next transition; it returns False once none is possible.
    while model.step():
        if should_stop(model, ctx):
            break

    sample_dir = data_dir / str(sample_id)
    sample_dir.mkdir(parents=True)
    write_outputs(model, sample_dir)
    # One column per context parameter, then rejections and run time.
    return {
        **asdict(ctx),
        # Every trial is accepted, but the column is kept for a uniform layout.
        "n_rejections": 0,
        "total_time": perf_counter() - start,
    }


def main() -> None:
    """Generate each split of the dataset."""
    # The master seed gives one seed per split, drawn in order even for the
    # splits that are skipped, so every split is reproducible on its own.
    rng = Random(SEED)
    for split, n_samples in N_SAMPLES.items():
        split_dir = OUTPUT_DIR / split
        split_seed = rng.getrandbits(32)
        # Existing splits are skipped, not overwritten.
        if split_dir.exists():
            print(f"Output directory {split_dir} already exists. Skipping.")
            continue
        split_dir.mkdir(parents=True)
        # Run the samples in parallel and collect one metadata row per sample.
        metadata = run_simulations(
            n_samples,
            partial(simulate, data_dir=split_dir / "data"),
            seed=split_seed,
            n_jobs=N_JOBS,
        )
        metadata.to_csv(split_dir / "metadata.csv", index=False)


if __name__ == "__main__":
    main()
