"""Simulation utilities."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

import joblib
import pandas as pd
from tqdm import tqdm

if TYPE_CHECKING:
    from collections.abc import Callable

    from phyloom.types import Metadata, SampleID, Seed


def run_simulations(
    n_samples: int,
    sim_func: Callable[[SampleID, Seed], Metadata],
    *,
    seed: Seed | None = None,
    n_jobs: int = -1,
) -> pd.DataFrame:
    """Run independent simulations in parallel and collect their metadata.

    Args:
        n_samples: Number of simulations to run. Sample IDs are assigned
            sequentially from ``1`` to ``n_samples``.
        sim_func: Function that runs one simulation for a sample ID and
            random seed, returning that sample's metadata.
        seed: Seed used to derive the per-sample seeds. If ``None``, use a
            non-deterministic seed source.
        n_jobs: Number of parallel workers passed to :class:`joblib.Parallel`.

    Returns:
        A data frame containing one row of metadata per sample, sorted by
        ``sample_id``.
    """

    def run_sample(i: SampleID, seed: Seed) -> dict[str, object]:
        return {"sample_id": i, **sim_func(i, seed)}

    rng = Random(seed)
    jobs = joblib.Parallel(n_jobs=n_jobs, return_as="generator_unordered")(
        joblib.delayed(run_sample)(i=i, seed=rng.getrandbits(32))
        for i in range(1, n_samples + 1)
    )

    df = pd.DataFrame([md for md in tqdm(jobs, "Running...", n_samples)])
    df = df.sort_values("sample_id")
    return df
