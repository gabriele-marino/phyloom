"""Susceptible-exposed-infectious-recovered (SEIR).

SIR with an incubation stage. Infected hosts are lineages, either exposed
(state `E`: infected but not yet infectious) or infectious (state `I`), while
susceptible (`S`) and recovered (`R`) hosts are pools. `I` lineages infect
susceptible hosts, creating `E` lineages; `E` lineages become infectious after
a mean time `T_E`; `I` lineages recover at rate μ = 1 / T_I, a fraction `s` of
them sampled.

Run it from the repository root with `python examples/python/SEIR.py`.
`examples/yaml/SEIR.yaml` builds the same model as a YAML configuration
and explains its specifics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.core import Event
from phyloom.simulator.epidemic import EpidemicModel, Infection, Migration, Recovery
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

# Dataset settings.
OUTPUT_DIR = Path("outputs/SEIR-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    """The parameters of one sample."""

    R_0: float
    T_E: float
    T_I: float
    mu: float
    s: float
    init_S: int
    la: float


def draw_context(rng: np.random.Generator) -> Context:
    """Draw the parameters of one sample."""
    R_0 = rng.uniform(low=1.5, high=4)
    T_E = rng.uniform(low=1, high=5)
    T_I = rng.uniform(low=5, high=20)
    mu = 1 / T_I
    s = rng.uniform(low=0.2, high=0.5)
    init_S = int(rng.integers(low=200, high=1001))
    return Context(
        R_0=R_0,
        T_E=T_E,
        T_I=T_I,
        mu=mu,
        s=s,
        init_S=init_S,
        la=R_0 * mu / init_S,
    )


def build_model(ctx: Context) -> EpidemicModel:
    """Build a fresh model for one trial."""
    return EpidemicModel(
        init_state="I",
        init_pools={"S": ctx.init_S},
        events=[
            Event(
                Infection(
                    recipient_pool="S", source_state="I", child_states=("I", "E")
                ),
                ConstantHazard(ctx.la),
            ),
            Event(
                Recovery(destination_pool="R", source_state="I"),
                ConstantHazard(ctx.mu * (1 - ctx.s)),
            ),
            Event(
                Recovery(destination_pool="R", source_state="I", sample=True),
                ConstantHazard(ctx.mu * ctx.s),
            ),
            Event(
                Migration(source_state="E", target_state="I"),
                ConstantHazard(1 / ctx.T_E),
            ),
        ],
    )


def should_stop(model: EpidemicModel, ctx: Context) -> bool:
    """The stop criterion, checked after every step."""
    return model.count_sampled_lineages() == 20


def is_accepted(model: EpidemicModel, ctx: Context) -> bool:
    """The acceptance criterion, checked once a trial has stopped."""
    return model.count_current_lineages() > 0


def logs(model: EpidemicModel, ctx: Context) -> dict[str, object]:
    """Extra `metadata.csv` columns."""
    return {
        "still_susceptible": model.pools["S"],
        "recovered": model.pools["R"],
        "still_incubating": model.count_current_lineages("E"),
    }


def write_outputs(model: EpidemicModel, sample_dir: Path) -> None:
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
