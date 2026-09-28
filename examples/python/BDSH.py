"""Birth-death-sampling-hybridization (BDSH) networks.

Lineages branch and are sampled without being removed, while pairs of
lineages hybridize through three competing events: lineage-degenerative
(LDH), lineage-neutral (LNH), and lineage-generative (LGH) hybridization. Each
event has its own rate, drawn independently for each sample, so the dataset
covers networks dominated by one kind of hybridization as well as mixtures.

Run it from the repository root with `python examples/python/BDSH.py`.
`examples/yaml/BDSH.yaml` builds the same model as a YAML configuration
and explains its specifics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.core import Net
from phyloom.simulator.bdsh import LDH, LGH, LNH, BDSHModel, Birth, Sampling
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

# Dataset settings.
OUTPUT_DIR = Path("outputs/BDSH-python")
N_SAMPLES = {"train": 10, "val": 2, "test": 2}
N_JOBS = -1
SEED = 45


@dataclass(frozen=True)
class Context:
    """The parameters of one sample."""

    la: float
    sampling_rate: float
    n_leaves: int
    ldh_rate: float
    lnh_rate: float
    lgh_rate: float


def draw_context(rng: np.random.Generator) -> Context:
    """Draw the parameters of one sample."""
    return Context(
        la=0.5,
        sampling_rate=0.25,
        n_leaves=50,
        ldh_rate=rng.uniform(low=0.0005, high=0.003),
        lnh_rate=rng.uniform(low=0.0005, high=0.003),
        lgh_rate=rng.uniform(low=0.0005, high=0.003),
    )


def build_model(ctx: Context) -> BDSHModel:
    """Build a fresh model for one trial."""
    return BDSHModel(
        init_state="A",
        events=[
            Event(Birth(), ConstantHazard(ctx.la)),
            Event(Sampling(removal=False), ConstantHazard(ctx.sampling_rate)),
            Event(LDH(hybrid_state="H_LDH"), ConstantHazard(ctx.ldh_rate)),
            Event(LNH(hybrid_state="H_LNH"), ConstantHazard(ctx.lnh_rate)),
            Event(LGH(hybrid_state="H_LGH"), ConstantHazard(ctx.lgh_rate)),
        ],
    )


def sampled_network(model: BDSHModel) -> Net[float]:
    """The network ancestral to the sampled lineages."""
    return model.history(model.get_sampled_lineages())


def count_reticulations(network: Net[float]) -> int:
    """Number of reticulations in `network`."""
    return network.n_edges - network.n_nodes + 1


def should_stop(model: BDSHModel, ctx: Context) -> bool:
    """The stop criterion, checked after every step."""
    return model.count_sampled_lineages() == ctx.n_leaves


def is_accepted(model: BDSHModel, ctx: Context) -> bool:
    """The acceptance criterion, checked once a trial has stopped."""
    return count_reticulations(sampled_network(model)) > 0


def logs(model: BDSHModel, ctx: Context) -> dict[str, object]:
    """Extra `metadata.csv` columns."""
    network = sampled_network(model)
    return {
        "sampled_tips": network.count_leaves(),
        "reticulations": count_reticulations(network),
    }


def write_outputs(model: BDSHModel, sample_dir: Path) -> None:
    """Write the files of an accepted trial to the sample's folder."""
    model.history().dump(sample_dir / "history.nwk")
    sampled_network(model).dump(sample_dir / "sampled-network.nwk")


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
