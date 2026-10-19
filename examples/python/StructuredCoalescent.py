from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from random import Random
from time import perf_counter

import numpy as np

from phyloom.simulator.coalescent import Coalesce, CoalescentModel, Retrace
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard
from phyloom.simulator.utils import run_simulations

OUTPUT_DIR = Path("outputs/StructuredCoalescent-python")
N_SAMPLES = {"train": 10, "val": 2, "test": 2}
N_JOBS = -1
SEED = 43


@dataclass(frozen=True)
class Context:
    effective_population_size: int
    coalescence_rate: float
    migration_rate: float


def draw_context(rng: np.random.Generator) -> Context:
    effective_population_size = 1
    return Context(
        effective_population_size=effective_population_size,
        coalescence_rate=1 / (2 * effective_population_size),
        migration_rate=0.5,
    )


def build_model(ctx: Context) -> CoalescentModel:
    return CoalescentModel(
        init_population={"A": 4, "B": 4},
        events=[
            Event(
                Retrace(ancestral_state="B", current_state="A"),
                ConstantHazard(ctx.migration_rate),
            ),
            Event(
                Retrace(ancestral_state="A", current_state="B"),
                ConstantHazard(ctx.migration_rate),
            ),
            Event(
                Coalesce(current_states=("A", "A"), ancestral_state="A"),
                ConstantHazard(ctx.coalescence_rate),
            ),
            Event(
                Coalesce(current_states=("B", "B"), ancestral_state="B"),
                ConstantHazard(ctx.coalescence_rate),
            ),
        ],
    )


def should_stop(model: CoalescentModel, ctx: Context) -> bool:
    return model.count_current_lineages() == 1


def write_outputs(model: CoalescentModel, sample_dir: Path) -> None:
    model.history().dump(sample_dir / "genealogy.nwk")


def simulate(sample_id: int, seed: int, *, data_dir: Path) -> dict[str, object]:
    rng = Random(seed)
    start = perf_counter()
    ctx = draw_context(np.random.default_rng(rng.getrandbits(32)))

    model = build_model(ctx)
    model.rng.seed(rng.getrandbits(32))
    while model.step():
        if should_stop(model, ctx):
            break

    sample_dir = data_dir / str(sample_id)
    sample_dir.mkdir(parents=True)
    write_outputs(model, sample_dir)
    return {
        **asdict(ctx),
        "n_rejections": 0,
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
