"""Benchmark phyloom against treesimulator: run time and peak memory.

Both simulators generate trees with a growing number of sampled tips under
the same constant-rate birth-death (BD) model. Treesimulator is used for
comparison because it is, like phyloom, a pure-Python simulator that
simulates the full transmission history and extracts the sampled tree from it.
Each simulator is run until a tree with exactly the target number of sampled
tips is produced, retrying on early extinction.

The results are saved to `benchmarks.csv`, which is only regenerated if it does
not exist yet, plotted to `benchmarks.svg`, and summarized in the console.

Run from the repository root with the `benchmarks` dependency group:

    uv run --group benchmarks benchmarks/run.py
"""

import time
import tracemalloc
from itertools import product
from pathlib import Path
from random import Random

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import NullLocator
from tqdm import tqdm
from treesimulator.generator import generate  # pyright: ignore
from treesimulator.mtbd_models import BirthDeathModel  # pyright: ignore

from phyloom.simulator.bdsh import BDSHModel, Birth, Death, Sampling
from phyloom.simulator.core import Event
from phyloom.simulator.hazards import ConstantHazard

CSV_PATH = Path(__file__).parent / "benchmarks.csv"
SEED = 42
N_REPLICATES = 5
N_LEAVES = [500, 1000, 2000, 4000]

LA = 1.2
MU = 0.4
P = 0.5


def run_phyloom(n_leaves: int, seed: int):
    """Run phyloom trials until a tree with exactly `n_leaves` tips is produced."""
    rng = Random(seed)
    while True:
        model = BDSHModel(
            init_state="I",
            events=[
                Event(Birth(), ConstantHazard(LA)),
                Event(Death(), ConstantHazard(MU * (1 - P))),
                Event(Sampling(removal=True), ConstantHazard(MU * P)),
            ],
        )
        model.rng.seed(rng.getrandbits(32))
        while model.step():
            if model.count_sampled_lineages() == n_leaves:
                model.history(model.get_sampled_lineages())
                return


def run_treesimulator(n_leaves: int, seed: int):
    """Run treesimulator trials until a tree with exactly `n_leaves` tips is produced."""
    rng = Random(seed)
    while True:
        epidemic = generate(
            [BirthDeathModel(la=LA, psi=MU, p=P)],
            max_tips=n_leaves,
            root_state="I",
            random_seed=rng.getrandbits(32),
        )
        if epidemic.n_tips == n_leaves:  # pyright: ignore
            return


def benchmark() -> None:
    """Measure the wall-clock time and the peak memory of each simulator run."""
    runners = [("phyloom", run_phyloom), ("treesimulator", run_treesimulator)]
    runs = list(product(N_LEAVES, range(N_REPLICATES), runners))
    rows: list[dict[str, object]] = []
    for n_leaves, replicate, (tool, run) in tqdm(runs, "Benchmarking", unit="run"):
        start = time.perf_counter()
        run(n_leaves, SEED + replicate)
        elapsed = time.perf_counter() - start

        tracemalloc.start()
        run(n_leaves, SEED + replicate)
        memory = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()

        rows.append(
            {"n_leaves": n_leaves, "tool": tool, "time": elapsed, "memory": memory}
        )
    pd.DataFrame(rows).to_csv(CSV_PATH, index=False)


def main() -> None:
    if not CSV_PATH.exists():
        benchmark()
    df = pd.read_csv(CSV_PATH)
    means = df.groupby(["tool", "n_leaves"])[["time", "memory"]].mean()
    stds = df.groupby(["tool", "n_leaves"])[["time", "memory"]].std()
    phyloom, treesimulator = means.loc["phyloom"], means.loc["treesimulator"]
    xs = np.array(N_LEAVES)

    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3), layout="constrained")  # pyright: ignore
    for ax, metric, ylabel in zip(
        axes, ["time", "memory"], ["Wall-clock time (s)", "Peak memory (MB)"]
    ):
        for tool, marker in [("phyloom", "o"), ("treesimulator", "s")]:
            ax.errorbar(
                xs,
                means.loc[tool][metric],
                yerr=stds.loc[tool][metric],
                marker=marker,
                label=tool,
            )
        scale = (phyloom[metric] / xs).mean()
        ax.plot(xs, scale * xs, "k--", label="linear")
        ax.set(xscale="log", yscale="log", xlabel="Sampled tips", ylabel=ylabel)
        ax.set_xticks(xs, xs)
        ax.xaxis.set_minor_locator(NullLocator())
        ax.grid(color="0.9")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncols=3, frameon=False)  # pyright: ignore
    fig.savefig(CSV_PATH.with_suffix(".svg"))  # pyright: ignore

    speedup = treesimulator["time"] / phyloom["time"]
    memory_ratio = phyloom["memory"] / treesimulator["memory"]
    for n_leaves in N_LEAVES:
        print(
            f"{n_leaves} tips: phyloom is {speedup[n_leaves]:.1f}-fold faster and uses "
            f"{memory_ratio[n_leaves]:.1f}-fold more memory"
        )
    for metric in ["time", "memory"]:
        slope = np.polyfit(np.log(xs), np.log(phyloom[metric]), 1)[0]
        print(f"Log-log slope of the phyloom {metric}: {slope:.2f} (1 is linear)")
    units = xs / P
    ms = 1e3 * np.sum(units * phyloom["time"]) / np.sum(units**2)
    kb = 1e3 * np.sum(units * phyloom["memory"]) / np.sum(units**2)
    print(f"Phyloom cost per unit of n/p: {ms:.3f} ms and {kb:.1f} kB")
    print(f"16 GB of RAM allow n/p up to about {16e6 / kb / 1e6:.1f} million")


if __name__ == "__main__":
    main()
