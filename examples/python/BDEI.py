"""Birth-death with exposed and infectious stages (BDEI).

Newly infected lineages start exposed (state `E`): they neither transmit nor
are removed, and become infectious (state `I`) at rate ε. Infectious lineages
transmit at rate λ, creating new `E` lineages, and are removed at rate μ; each
removal is sampled with probability p.

Run it from the repository root with `python examples/python/BDEI.py`.
`examples/yaml/BDEI.yaml` builds the same model as a YAML configuration
and explains its specifics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.bdsh import BDSHModel, Birth, Death, Migration, Sampling
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

# Dataset settings.
OUTPUT_DIR = Path("outputs/BDEI-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    """The parameters of one sample."""

    R_0: float
    T: float
    f: float
    T_I: float
    T_E: float
    epsilon: float
    mu: float
    p: float
    la: float
    psi: float
    death_rate: float
    init_state: str
    n_leaves: int


def draw_context(rng: np.random.Generator) -> Context:
    """Draw the parameters of one sample."""
    R_0 = rng.lognormal(mean=1.0, sigma=0.2)
    T = rng.lognormal(mean=1.0, sigma=0.3)
    f = rng.uniform(low=0.05, high=0.75)
    T_I = (1 - f) * T
    T_E = f * T
    mu = 1 / T_I
    p = rng.uniform(low=0.05, high=0.75)
    psi = mu * p
    return Context(
        R_0=R_0,
        T=T,
        f=f,
        T_I=T_I,
        T_E=T_E,
        epsilon=1 / T_E,
        mu=mu,
        p=p,
        la=R_0 * mu,
        psi=psi,
        death_rate=mu - psi,
        init_state=str(rng.choice(["E", "I"], p=[0.8, 0.2])),
        n_leaves=int(rng.integers(low=50, high=251)),
    )


def build_model(ctx: Context) -> BDSHModel:
    """Build a fresh model for one trial."""
    return BDSHModel(
        init_state=ctx.init_state,
        events=[
            Event(
                Birth(parent_state="I", child_states=("I", "E")),
                ConstantHazard(ctx.la),
            ),
            Event(
                Migration(source_state="E", target_state="I"),
                ConstantHazard(ctx.epsilon),
            ),
            Event(Death(state="I"), ConstantHazard(ctx.death_rate)),
            Event(Sampling(state="I", removal=True), ConstantHazard(ctx.psi)),
        ],
    )


def should_stop(model: BDSHModel, ctx: Context) -> bool:
    """The stop criterion, checked after every step."""
    return model.count_sampled_lineages() == ctx.n_leaves


def is_accepted(model: BDSHModel, ctx: Context) -> bool:
    """The acceptance criterion, checked once a trial has stopped."""
    return model.count_current_lineages() > 0


def logs(model: BDSHModel, ctx: Context) -> dict[str, object]:
    """Extra `metadata.csv` columns."""
    return {
        "still_incubating": model.count_current_lineages("E"),
        "still_infectious": model.count_current_lineages("I"),
    }


def write_outputs(model: BDSHModel, sample_dir: Path) -> None:
    """Write the files of an accepted trial to the sample's folder."""
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
        # step() applies the next transition; it returns False once none is possible.
        while model.step():
            if should_stop(model, ctx):
                break
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
