from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np
import pandas as pd

from phyloom.simulator.bdsh import BDSHModel, Birth, Death, Migration, Sampling
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

OUTPUT_DIR = Path("outputs/BiSSE-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42
MAX_REJECTIONS = 10


@dataclass(frozen=True)
class Context:
    la_A: float
    la_B: float
    mu_A: float
    mu_B: float
    psi: float
    m: float
    init_state: str
    max_time: float
    rho_sample_A: float
    rho_sample_B: float


def draw_context(rng: np.random.Generator) -> Context:
    la_A = rng.uniform(low=0.1, high=0.3)
    la_B = rng.uniform(low=la_A, high=2 * la_A)
    return Context(
        la_A=la_A,
        la_B=la_B,
        mu_A=rng.uniform(low=la_A / 5, high=la_A / 2),
        mu_B=rng.uniform(low=la_B / 5, high=la_B / 2),
        psi=rng.uniform(low=0.001, high=0.005),
        m=rng.uniform(low=0.01, high=0.05),
        init_state=str(rng.choice(["A", "B"], p=[0.5, 0.5])),
        max_time=rng.uniform(low=10, high=20),
        rho_sample_A=rng.uniform(low=0.5, high=0.9),
        rho_sample_B=rng.uniform(low=0.5, high=0.9),
    )


def sample_present(model: BDSHModel, ctx: Context) -> None:
    model.rho_sample(ctx.rho_sample_A, "A", removal=False)
    model.rho_sample(ctx.rho_sample_B, "B", removal=False)


def build_model(ctx: Context) -> BDSHModel:
    return BDSHModel(
        init_state=ctx.init_state,
        events=[
            Event(Birth(parent_state="A"), ConstantHazard(ctx.la_A)),
            Event(Birth(parent_state="B"), ConstantHazard(ctx.la_B)),
            Event(Death(state="A"), ConstantHazard(ctx.mu_A)),
            Event(Death(state="B"), ConstantHazard(ctx.mu_B)),
            Event(Migration(source_state="A", target_state="B"), ConstantHazard(ctx.m)),
            Event(Migration(source_state="B", target_state="A"), ConstantHazard(ctx.m)),
            Event(Sampling(removal=False), ConstantHazard(ctx.psi)),
        ],
        schedule=[(ctx.max_time, partial(sample_present, ctx=ctx))],
    )


def is_accepted(model: BDSHModel, ctx: Context) -> bool:
    return (
        model.count_sampled_lineages("A") > 10
        and model.count_sampled_lineages("B") > 10
    )


def write_outputs(model: BDSHModel, sample_dir: Path) -> None:
    model.history(model.get_sampled_lineages()).dump(sample_dir / "sampled.nwk")


def simulate(sample_id: int, seed: int, *, data_dir: Path) -> dict[str, object]:
    rng = Random(seed)
    start = perf_counter()
    abandoned: list[Context] = []
    while True:
        ctx = draw_context(np.random.default_rng(rng.getrandbits(32)))
        for n_rejections in range(MAX_REJECTIONS + 1):
            model = build_model(ctx)
            model.rng.seed(rng.getrandbits(32))
            while model.step(ctx.max_time):
                pass
            if is_accepted(model, ctx):
                break
        else:
            abandoned.append(ctx)
            continue
        break

    sample_dir = data_dir / str(sample_id)
    sample_dir.mkdir(parents=True)
    write_outputs(model, sample_dir)
    return {
        **asdict(ctx),
        "n_rejections": n_rejections,
        "total_time": perf_counter() - start,
        "abandoned": [asdict(c) for c in abandoned],
    }


def main() -> None:
    rng = Random(SEED)
    for split, n_samples in N_SAMPLES.items():
        split_dir = OUTPUT_DIR / split
        split_seed = rng.getrandbits(32)
        if split_dir.exists():
            print(f"Output directory {split_dir} already exists. Skipping.")
            continue
        split_dir.mkdir(parents=True)
        metadata = run_simulations(
            n_samples,
            partial(simulate, data_dir=split_dir / "data"),
            seed=split_seed,
            n_jobs=N_JOBS,
        )
        abandoned = pd.DataFrame(
            [ctx for contexts in metadata.pop("abandoned") for ctx in contexts]
        )
        if not abandoned.empty:
            abandoned.to_csv(
                split_dir / "max_rejections_exceeded_contexts.csv", index=False
            )
        metadata.to_csv(split_dir / "metadata.csv", index=False)


if __name__ == "__main__":
    main()
