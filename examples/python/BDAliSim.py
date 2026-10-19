from __future__ import annotations

import subprocess
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

OUTPUT_DIR = Path("outputs/BDAliSim-python")
N_SAMPLES = {"train": 100, "val": 10, "test": 10}
N_JOBS = -1
SEED = 42


@dataclass(frozen=True)
class Context:
    R_0: float
    mu: float
    p: float
    la: float
    death_rate: float
    psi: float
    n_leaves: int
    clock_rate: float
    seq_length: int
    alisim_seed: int


def draw_context(rng: np.random.Generator) -> Context:
    R_0 = rng.uniform(low=1.5, high=4.0)
    mu = rng.uniform(low=0.25, high=0.6)
    p = rng.uniform(low=0.1, high=0.5)
    return Context(
        R_0=R_0,
        mu=mu,
        p=p,
        la=R_0 * mu,
        death_rate=mu * (1 - p),
        psi=mu * p,
        n_leaves=int(rng.integers(low=20, high=41)),
        clock_rate=rng.uniform(low=0.001, high=0.01),
        seq_length=int(rng.integers(low=500, high=1001)),
        alisim_seed=int(rng.integers(low=1, high=2**31)),
    )


def build_model(ctx: Context) -> BDSHModel:
    return BDSHModel(
        init_state="I",
        events=[
            Event(Birth(), ConstantHazard(ctx.la)),
            Event(Death(), ConstantHazard(ctx.death_rate)),
            Event(Sampling(removal=True), ConstantHazard(ctx.psi)),
        ],
    )


def should_stop(model: BDSHModel, ctx: Context) -> bool:
    return model.count_sampled_lineages() == ctx.n_leaves


def is_accepted(model: BDSHModel, ctx: Context) -> bool:
    return model.count_current_lineages() > 0


def write_outputs(model: BDSHModel, ctx: Context, sample_dir: Path) -> None:
    model.history(model.get_sampled_lineages()).dump(sample_dir / "sampled.nwk")
    result = subprocess.run(
        [
            "iqtree3",
            "--alisim",
            str(sample_dir / "alignment"),
            "-t",
            str(sample_dir / "sampled.nwk"),
            "-m",
            "JC",
            "--length",
            str(ctx.seq_length),
            "--branch-scale",
            str(ctx.clock_rate),
            "--seed",
            str(ctx.alisim_seed),
            "-af",
            "fasta",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"AliSim failed with exit status {result.returncode}: "
            f"{result.stderr.strip()}"
        )


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
    write_outputs(model, ctx, sample_dir)
    return {
        **asdict(ctx),
        "n_rejections": n_rejections,
        "total_time": perf_counter() - start,
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
