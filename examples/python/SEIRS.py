from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.core import Event
from phyloom.simulator.epidemic import (
    EpidemicModel,
    Flow,
    Infection,
    Migration,
    Recovery,
)
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

OUTPUT_DIR = Path("outputs/SEIRS-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    R_0: float
    T_E: float
    T_I: float
    T_R: float
    omega: float
    mu: float
    s: float
    init_S: int
    la: float


def draw_context(rng: np.random.Generator) -> Context:
    R_0 = rng.uniform(low=1.5, high=4)
    T_E = rng.uniform(low=1, high=5)
    T_I = rng.uniform(low=5, high=20)
    T_R = rng.uniform(low=3 * T_I, high=10 * T_I)
    mu = 1 / T_I
    s = rng.uniform(low=0.2, high=0.5)
    init_S = int(rng.integers(low=100, high=200))
    return Context(
        R_0=R_0,
        T_E=T_E,
        T_I=T_I,
        T_R=T_R,
        omega=1 / T_R,
        mu=mu,
        s=s,
        init_S=init_S,
        la=R_0 * mu / init_S,
    )


def build_model(ctx: Context) -> EpidemicModel:
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
            Event(
                Flow(source_pool="R", destination_pool="S"), ConstantHazard(ctx.omega)
            ),
        ],
    )


def should_stop(model: EpidemicModel, ctx: Context) -> bool:
    return model.count_sampled_lineages() == 100


def is_accepted(model: EpidemicModel, ctx: Context) -> bool:
    return model.count_current_lineages() > 0


def logs(model: EpidemicModel, ctx: Context) -> dict[str, object]:
    return {
        "still_susceptible": model.pools["S"],
        "recovered": model.pools["R"],
        "still_incubating": model.count_current_lineages("E"),
    }


def write_outputs(model: EpidemicModel, sample_dir: Path) -> None:
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
