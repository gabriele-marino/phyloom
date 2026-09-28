"""Diversity-dependent diversification with competitive replacement.

A clade of non-innovating lineages (state `N`) diversifies until it
approaches a carrying capacity `K`. `N` lineages occasionally acquire a key
innovation and become innovating lineages (state `I`), which speciate faster.
Speciation of both states slows down as the clade fills up, and the
extinction rate of `N` lineages grows with the number of `I` lineages, so
innovators progressively replace incumbents. At the present (`max_time`), a
fraction `rho` of the surviving lineages is sampled.

Run it from the repository root with `python examples/python/DiversityDependent.py`.
`examples/yaml/DiversityDependent.yaml` builds the same model as a YAML configuration
and explains its specifics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.bdsh import BDSHModel, Birth, Death, Migration
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

# Dataset settings.
OUTPUT_DIR = Path("outputs/DiversityDependent-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    """The parameters of one sample."""

    K: int
    la_N: float
    mu_N: float
    r_I: float
    la_I: float
    mu_I: float
    q: float
    alpha: float
    max_time: float
    rho: float


def draw_context(rng: np.random.Generator) -> Context:
    """Draw the parameters of one sample."""
    K = int(rng.integers(low=50, high=101))
    la_N = rng.uniform(low=0.2, high=0.4)
    mu_N = rng.uniform(low=0.02, high=0.05)
    r_I = rng.uniform(low=1.5, high=3)
    return Context(
        K=K,
        la_N=la_N,
        mu_N=mu_N,
        r_I=r_I,
        la_I=r_I * la_N,
        mu_I=rng.uniform(low=0.02, high=0.05),
        q=rng.uniform(low=0.002, high=0.01),
        alpha=rng.uniform(low=0.02, high=0.1),
        max_time=rng.uniform(low=40, high=60),
        rho=rng.uniform(low=0.5, high=1.0),
    )


def sample_present(model: BDSHModel, ctx: Context) -> None:
    """Sample the surviving lineages at the present, without removal."""
    model.rho_sample(ctx.rho, "N", removal=False)
    model.rho_sample(ctx.rho, "I", removal=False)


def build_model(ctx: Context) -> BDSHModel:
    """Build a fresh model for one trial."""

    def room_to_speciate(model: BDSHModel) -> float:
        return max(0.0, 1 - model.count_current_lineages() / ctx.K)

    def competition(model: BDSHModel) -> float:
        return 1 + ctx.alpha * model.count_current_lineages("I")

    return BDSHModel(
        init_state="N",
        events=[
            Event(
                Birth(parent_state="N"),
                ConstantHazard(ctx.la_N),
                rate_multiplier=room_to_speciate,
            ),
            Event(
                Birth(parent_state="I"),
                ConstantHazard(ctx.la_I),
                rate_multiplier=room_to_speciate,
            ),
            Event(
                Death(state="N"),
                ConstantHazard(ctx.mu_N),
                rate_multiplier=competition,
            ),
            Event(Death(state="I"), ConstantHazard(ctx.mu_I)),
            Event(Migration(source_state="N", target_state="I"), ConstantHazard(ctx.q)),
        ],
        schedule=[(ctx.max_time, partial(sample_present, ctx=ctx))],
    )


def is_accepted(model: BDSHModel, ctx: Context) -> bool:
    """The acceptance criterion, checked once a trial has stopped."""
    return (
        model.count_sampled_lineages() >= 20 and model.count_sampled_lineages("I") >= 5
    )


def logs(model: BDSHModel, ctx: Context) -> dict[str, object]:
    """Extra `metadata.csv` columns."""
    return {
        "extant_N": model.count_current_lineages("N"),
        "extant_I": model.count_current_lineages("I"),
    }


def write_outputs(model: BDSHModel, sample_dir: Path) -> None:
    """Write the files of an accepted trial to the sample's folder."""
    model.history().dump(sample_dir / "history.nwk")
    model.history(model.get_sampled_lineages()).dump(sample_dir / "sampled.nwk")


def simulate(sample_id: int, seed: int, *, data_dir: Path) -> dict[str, object]:
    """Generate one accepted sample and return its `metadata.csv` row.

    `run_simulations` calls this once per sample, with the sample id and a
    seed derived from the split's seed.
    """
    # The sample's random stream gives one seed for the context draws, then one
    # seed for the model of each trial.
    rng = Random(seed)
    start = perf_counter()
    ctx = draw_context(np.random.default_rng(rng.getrandbits(32)))

    n_rejections = 0
    while True:
        model = build_model(ctx)
        model.rng.seed(rng.getrandbits(32))
        # step() takes an upper bound on simulated time; it returns False once
        # no transition is possible before it.
        while model.step(ctx.max_time):
            pass
        if is_accepted(model, ctx):
            break
        # A rejected trial is retried with the same parameters.
        n_rejections += 1

    sample_dir = data_dir / str(sample_id)
    sample_dir.mkdir(parents=True)
    write_outputs(model, sample_dir)
    # One column per context parameter, then rejections, run time, and logs.
    return {
        **asdict(ctx),
        "n_rejections": n_rejections,
        "total_time": perf_counter() - start,
        **logs(model, ctx),
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
