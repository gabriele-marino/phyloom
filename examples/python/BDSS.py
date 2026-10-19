from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.bdsh import BDSHModel, Birth, Death, Sampling
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

OUTPUT_DIR = Path("outputs/BDSS-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    R_0: float
    T_I: float
    mu: float
    p: float
    psi: float
    death_rate: float
    r_SS: float
    f_SS: float
    R_0_NS: float
    R_0_SN: float
    R_0_S: float
    R_0_N: float
    lambda_NN: float
    lambda_SS: float
    lambda_NS: float
    lambda_SN: float
    init_state: str
    n_leaves: int


def draw_context(rng: np.random.Generator) -> Context:
    R_0 = rng.lognormal(mean=1.0, sigma=0.2)
    T_I = 2.5
    mu = 1 / T_I
    p = 0.25
    psi = mu * p
    r_SS = rng.uniform(low=2, high=10)
    f_SS = rng.uniform(low=0.1, high=0.3)
    R_0_NS = R_0 * f_SS / (1 + r_SS * f_SS - f_SS)
    R_0_SN = (R_0 - r_SS * R_0_NS) * r_SS
    R_0_S = r_SS * R_0_NS
    R_0_N = R_0_SN / r_SS
    return Context(
        R_0=R_0,
        T_I=T_I,
        mu=mu,
        p=p,
        psi=psi,
        death_rate=mu - psi,
        r_SS=r_SS,
        f_SS=f_SS,
        R_0_NS=R_0_NS,
        R_0_SN=R_0_SN,
        R_0_S=R_0_S,
        R_0_N=R_0_N,
        lambda_NN=R_0_N * mu,
        lambda_SS=R_0_S * mu,
        lambda_NS=R_0_NS * mu,
        lambda_SN=R_0_SN * mu,
        init_state=str(rng.choice(["I_N", "I_S"], p=[1 - f_SS, f_SS])),
        n_leaves=int(rng.integers(low=50, high=251)),
    )


def build_model(ctx: Context) -> BDSHModel:
    return BDSHModel(
        init_state=ctx.init_state,
        events=[
            Event(Birth(parent_state="I_N"), ConstantHazard(ctx.lambda_NN)),
            Event(Birth(parent_state="I_S"), ConstantHazard(ctx.lambda_SS)),
            Event(
                Birth(parent_state="I_N", child_states=("I_N", "I_S")),
                ConstantHazard(ctx.lambda_NS),
            ),
            Event(
                Birth(parent_state="I_S", child_states=("I_S", "I_N")),
                ConstantHazard(ctx.lambda_SN),
            ),
            Event(Death(), ConstantHazard(ctx.death_rate)),
            Event(Sampling(removal=True), ConstantHazard(ctx.psi)),
        ],
    )


def should_stop(model: BDSHModel, ctx: Context) -> bool:
    return model.count_sampled_lineages() == ctx.n_leaves


def is_accepted(model: BDSHModel, ctx: Context) -> bool:
    return model.count_current_lineages() > 0


def logs(model: BDSHModel, ctx: Context) -> dict[str, object]:
    n_super_spreaders = model.count_current_lineages("I_S")
    return {"ss_frequency": n_super_spreaders / model.count_current_lineages()}


def write_outputs(model: BDSHModel, sample_dir: Path) -> None:
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
