from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.bdsh import BDSHModel, Birth, Death, Sampling
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard, NumericHazard
from phyloom.simulator.utils import run_simulations

OUTPUT_DIR = Path("outputs/SeasonalBD-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    R_0: float
    mu: float
    la_0: float
    amplitude: float
    period: float
    peak_time: float
    p: float
    psi: float
    death_rate: float
    n_leaves: int


def draw_context(rng: np.random.Generator) -> Context:
    R_0 = rng.lognormal(mean=1.0, sigma=0.2)
    mu = rng.uniform(low=0.25, high=0.6)
    amplitude = rng.uniform(low=0.3, high=0.9)
    peak_time = rng.uniform(low=0.0, high=1.0)
    p = rng.uniform(low=0.1, high=0.4)
    return Context(
        R_0=R_0,
        mu=mu,
        la_0=R_0 * mu,
        amplitude=amplitude,
        period=1.0,
        peak_time=peak_time,
        p=p,
        psi=mu * p,
        death_rate=mu - mu * p,
        n_leaves=int(rng.integers(low=20, high=41)),
    )


def build_model(ctx: Context) -> BDSHModel:

    def seasonal_birth_rate(t: float) -> float:
        phase = 2 * np.pi * (t - ctx.peak_time) / ctx.period
        return ctx.la_0 * (1 + ctx.amplitude * np.cos(phase))

    return BDSHModel(
        init_state="I",
        events=[
            Event(
                Birth(),
                NumericHazard(seasonal_birth_rate, initial_dt=1 / ctx.la_0),
            ),
            Event(Death(), ConstantHazard(ctx.death_rate)),
            Event(Sampling(removal=True), ConstantHazard(ctx.psi)),
        ],
    )


def sampled_in_high_season(model: BDSHModel, ctx: Context) -> int:
    return sum(
        1
        for lineage in model.get_sampled_lineages()
        if np.cos(2 * np.pi * (model.time_of(lineage) - ctx.peak_time) / ctx.period) > 0
    )


def should_stop(model: BDSHModel, ctx: Context) -> bool:
    return model.count_sampled_lineages() == ctx.n_leaves


def is_accepted(model: BDSHModel, ctx: Context) -> bool:
    return model.count_current_lineages() > 0


def logs(model: BDSHModel, ctx: Context) -> dict[str, object]:
    return {"n_sampled_in_high_season": sampled_in_high_season(model, ctx)}


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
        while model.step():
            if should_stop(model, ctx):
                break
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
