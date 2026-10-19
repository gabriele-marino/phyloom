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

OUTPUT_DIR = Path("outputs/DiversityDependent-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
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
    model.rho_sample(ctx.rho, "N", removal=False)
    model.rho_sample(ctx.rho, "I", removal=False)


def build_model(ctx: Context) -> BDSHModel:

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
    return (
        model.count_sampled_lineages() >= 20 and model.count_sampled_lineages("I") >= 5
    )


def logs(model: BDSHModel, ctx: Context) -> dict[str, object]:
    return {
        "extant_N": model.count_current_lineages("N"),
        "extant_I": model.count_current_lineages("I"),
    }


def write_outputs(model: BDSHModel, sample_dir: Path) -> None:
    model.history().dump(sample_dir / "history.nwk")
    model.history(model.get_sampled_lineages()).dump(sample_dir / "sampled.nwk")


def simulate(sample_id: int, seed: int, *, data_dir: Path) -> dict[str, object]:
    rng = Random(seed)
    start = perf_counter()
    ctx = draw_context(np.random.default_rng(rng.getrandbits(32)))

    n_rejections = 0
    while True:
        model = build_model(ctx)
        model.rng.seed(rng.getrandbits(32))
        while model.step(ctx.max_time):
            pass
        if is_accepted(model, ctx):
            break
        n_rejections += 1

    sample_dir = data_dir / str(sample_id)
    sample_dir.mkdir(parents=True)
    write_outputs(model, sample_dir)
    return {
        **asdict(ctx),
        "n_rejections": n_rejections,
        "total_time": perf_counter() - start,
        **logs(model, ctx),
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
        metadata.to_csv(split_dir / "metadata.csv", index=False)


if __name__ == "__main__":
    main()
