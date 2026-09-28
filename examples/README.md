# 💡 Examples

These examples simulate classic models from macroevolution, phylodynamics, and population genetics with Phyloom's three built-in model families: birth-death processes with sampling and hybridization, compartmental epidemics, and the coalescent. None of them needs new code: every model is assembled from built-in event rules and hazards. To simulate a process that the built-in families cannot express, see [Plugins](https://github.com/gabriele-marino/phyloom/tree/main/plugins).

Each example is available in two equivalent forms, which produce the same dataset for the same seed:

- a **YAML configuration** in [`examples/yaml/`](https://github.com/gabriele-marino/phyloom/tree/main/examples/yaml), which the `phyloom` command runs directly, with no Python code needed.
- a **Python script** in [`examples/python/`](https://github.com/gabriele-marino/phyloom/tree/main/examples/python), which builds the same model with the Python API. Read it to see what happens underneath, or start from it to customize the pipeline in Python.

For complete references, see the [YAML user guide](https://gabriele-marino.github.io/phyloom/user_guide/yaml.html) and the [Python user guide](https://gabriele-marino.github.io/phyloom/user_guide/python.html).

## 🚀 Running an example

To run an example, you need [Python](https://www.python.org/downloads/) 3.10 or later. In the commands below, replace `<Model>` with the name of the example's files (for example, `BD`, `SIR`, or `Coalescent`).

1. Create and activate a virtual environment, then install Phyloom from PyPI. This also installs the `phyloom` command:

   ```bash
   python -m venv .venv
   source .venv/bin/activate       # on Windows: .venv\Scripts\activate
   pip install phyloom
   ```

2. Clone the repository and move into it:

   ```bash
   git clone https://github.com/gabriele-marino/phyloom.git
   cd phyloom
   ```

3. Run either form of the example:

   ```bash
   phyloom examples/yaml/<Model>.yaml       # YAML configuration
   python examples/python/<Model>.py        # equivalent Python script
   ```

4. Find the dataset in `outputs/<Model>-yaml` for the YAML file and `outputs/<Model>-python` for the script, with one folder per split.

   ```text
   outputs/<Model>-<yaml|python>/         
   ├── train/
   │   ├── data/<sample-id>/...   # files written by the output hooks
   │   └── metadata.csv           # context values, rejections, run time, and logs
   ├── val/
   └── test/
   ```

Splits that already exist are skipped, so delete the output folder (or change `output_dir` in the YAML file, `OUTPUT_DIR` in the script) to regenerate a dataset.

## 🔍 Reading an example

The files are commented throughout and meant to be read from top to bottom. Every YAML file opens with a header that describes the model, followed by the same five sections, and the matching script follows the same order, turning each section into constants or functions with the same names in every script:

| Section | YAML file | Python script |
| --- | --- | --- |
| **Dataset settings**: where the dataset is written, how many samples each split has, parallelism, and the master seed | `output_dir`, `n_samples`, `n_jobs`, `seed` | The constants `OUTPUT_DIR`, `N_SAMPLES`, `N_JOBS`, `SEED` |
| **Context**: the parameters of one sample, drawn anew for every sample and saved in `metadata.csv` | `context` | A frozen `Context` dataclass, and `draw_context`, which makes the same random draws in the same order |
| **Model**: the model family, its initial condition, and its events, each pairing a rule (what happens) with a hazard (how often) | `model` | `build_model`, which returns a fresh simulator object for each trial |
| **Trials**: when a trial ends and whether it is kept | `stop_criterion`, `max_time`, `acceptance_criterion`, `max_rejections` | `should_stop` and `is_accepted` |
| **Outputs**: extra `metadata.csv` columns and the files written for each sample | `logs`, `output_hooks` | `logs` and `write_outputs` |

In each Python script, `simulate` then runs the trials of one sample, and `main` generates the splits.

## Birth-death (BD)

![Birth-Death model.](../figures/examples/model-bd.svg)

Infectious lineages (state `I`) branch at rate $\lambda$ and are removed at rate $\mu$; each removal is sampled with probability $p$. Sampling effort increases at a random intervention time, as when testing is scaled up during an outbreak.

**Files:**
[`examples/yaml/BD.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/BD.yaml),
[`examples/python/BD.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/BD.py)

## Birth-death with exposed and infectious stages (BDEI)

![Birth-Death Exposed-Infectious model.](../figures/examples/model-bdei.svg)

Newly infected lineages start exposed (state `E`): they neither transmit nor are removed, and become infectious (state `I`) at rate $\varepsilon$. Infectious lineages transmit at rate $\lambda$, creating new `E` lineages, and are removed at rate $\mu$; each removal is sampled with probability $p$.

**Files:**
[`examples/yaml/BDEI.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/BDEI.yaml),
[`examples/python/BDEI.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/BDEI.py)

## Birth-death with super-spreaders (BDSS)

![Birth-Death super-spreading model.](../figures/examples/model-bdss.svg)

Infectious lineages are either ordinary (state `I_N`) or super-spreaders (state `I_S`), and each class can transmit to either class, giving four birth rates $\lambda_{NN}$, $\lambda_{NS}$, $\lambda_{SN}$, and $\lambda_{SS}$ (parent class first, offspring class second). Both classes are removed at rate $\mu$, and each removal is sampled with probability $p$.

**Files:**
[`examples/yaml/BDSS.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/BDSS.yaml),
[`examples/python/BDSS.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/BDSS.py)

## Binary-state speciation and extinction (BiSSE)

![BiSSE model.](../figures/examples/model-bisse.svg)

A binary trait, `A` or `B`, sets each lineage's speciation ($\lambda_A$, $\lambda_B$) and extinction ($\mu_A$, $\mu_B$) rates, and lineages switch trait at rate $m$. The clade is observed in two ways: fossil-like sampling at rate $\psi$ during the simulation, and sampling of a fraction $\rho_A$ or $\rho_B$ of the surviving lineages at the present ($T$), the end of the simulation.

**Files:**
[`examples/yaml/BiSSE.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/BiSSE.yaml),
[`examples/python/BiSSE.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/BiSSE.py)

## Diversity-dependent diversification

![Diversity-dependent model.](../figures/examples/model-diversity-dependent.svg)

A clade of non-innovating lineages (state `N`) diversifies until it approaches a carrying capacity $K$. `N` lineages occasionally acquire a key innovation and become innovating lineages (state `I`), which speciate faster. Speciation of both states slows down as the clade fills up, and the extinction rate of `N` lineages grows with the number of `I` lineages, so innovators progressively replace incumbents. At the present ($T$), a fraction $\rho$ of the surviving lineages is sampled.

**Files:**
[`examples/yaml/DiversityDependent.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/DiversityDependent.yaml),
[`examples/python/DiversityDependent.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/DiversityDependent.py)

## Birth-death-sampling-hybridization (BDSH)

Lineages branch and are sampled without being removed, while pairs of lineages hybridize through three competing events: lineage-degenerative (LDH), lineage-neutral (LNH), and lineage-generative (LGH) hybridization. Each event has its own rate, drawn independently for each sample, so the dataset covers networks dominated by one kind of hybridization as well as mixtures.

**Files:**
[`examples/yaml/BDSH.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/BDSH.yaml),
[`examples/python/BDSH.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/BDSH.py)

## Susceptible-infectious-recovered (SIR)

![SIR model.](../figures/examples/model-sir.svg)

A transmission tree in a finite host population. Susceptible (`S`) and recovered (`R`) hosts are pools, plain counts without ancestry; infectious hosts are lineages in state `I`. An infection consumes one susceptible host and creates a new `I` lineage, and an `I` lineage recovers into `R`, either unobserved at rate $\mu$ or sampled at rate $\psi$.

**Files:**
[`examples/yaml/SIR.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/SIR.yaml),
[`examples/python/SIR.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/SIR.py)

## Susceptible-exposed-infectious-recovered (SEIR)

![SEIR model.](../figures/examples/model-seir.svg)

SIR with an incubation stage. Infected hosts are lineages, either exposed (state `E`: infected but not yet infectious) or infectious (state `I`), while susceptible (`S`) and recovered (`R`) hosts are pools. `I` lineages infect susceptible hosts, creating `E` lineages; `E` lineages become infectious after a mean time $T_E$; `I` lineages recover at rate $\mu = 1 / T_I$, a fraction $s$ of them sampled.

**Files:**
[`examples/yaml/SEIR.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/SEIR.yaml),
[`examples/python/SEIR.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/SEIR.py)

## Susceptible-exposed-infectious-recovered-susceptible (SEIRS)

![SEIRS model.](../figures/examples/model-seirs.svg)

SEIR with waning immunity: each recovered host returns to the susceptible pool at rate $\omega = 1 / T_R$, where $T_R$ is the mean duration of immunity. Waning replenishes `S`, so the epidemic can persist instead of burning out.

**Files:**
[`examples/yaml/SEIRS.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/SEIRS.yaml),
[`examples/python/SEIRS.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/SEIRS.py)

## Kingman coalescent

The genealogy of lineages sampled from a single population of constant size. The simulation runs backward in time, from the samples at the present until they have all merged into one common ancestor. The initial lineages are the samples, and the whole genealogy is the output.

**Files:**
[`examples/yaml/Coalescent.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/Coalescent.yaml),
[`examples/python/Coalescent.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/Coalescent.py)

## Structured coalescent

The genealogy of lineages sampled from a population structured into two subpopulations (demes), `A` and `B`, connected by migration. Backward in time, lineages coalesce only within their deme and migrate between demes at a constant rate, so two lineages in different demes must come to share a deme before they can merge.

**Files:**
[`examples/yaml/StructuredCoalescent.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/StructuredCoalescent.yaml),
[`examples/python/StructuredCoalescent.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/StructuredCoalescent.py)

## Coalescent with exponential growth

The genealogy of lineages sampled from a population that has grown exponentially at rate $g$. Backward in time, the effective population size $N_e(t) = N_e(0) e^{-g t}$ shrinks, so the pairwise coalescence rate $1 / (2 N_e(t))$ grows as $e^{g t}$. Genealogies are star-like, with long terminal branches and ancestors compressed near the root.

**Files:**
[`examples/yaml/ExponentialGrowthCoalescent.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/examples/yaml/ExponentialGrowthCoalescent.yaml),
[`examples/python/ExponentialGrowthCoalescent.py`](https://github.com/gabriele-marino/phyloom/blob/main/examples/python/ExponentialGrowthCoalescent.py)
