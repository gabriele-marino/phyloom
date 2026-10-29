<p align="center">
  <img src="https://raw.githubusercontent.com/gabriele-marino/phyloom/main/figures/logo.svg" alt="Phyloom" width="620"/>
</p>

---

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/phyloom?style=flat-square&color=2A9D8F)](https://pypi.org/project/phyloom/)
[![Documentation](https://img.shields.io/badge/docs-website-6F42C1?style=flat-square)](https://gabriele-marino.github.io/phyloom/home)

[Phyloom](https://github.com/gabriele-marino/phyloom) is a flexible Python framework for designing and running stochastic phylogenetic tree and network simulators with minimal boilerplate. By handling core network and tree construction, the simulation loop, and data pipelines under the hood, Phyloom lets you focus on model design rather than implementation details.

You can work with pre-built model families, extend existing ones with custom event rules and rate functions, or implement brand-new models from scratch, all fully configurable via YAML or the Python API. Out of the box, Phyloom supports:

- **Birth-death-sampling-hybridization (BDSH)** models for forward-in-time branching processes with unbounded population growth, lineage sampling, and reticulation;
- **Coalescent models** to trace population ancestry backward in time;
- **Compartment-based epidemic models** for simulating the spread of infectious diseases in structured populations.

## ✨ Features

Phyloom comes packed with features, including:

- **Effortless tree and network simulation** 🌳🕸️  
  Simulate complex phylogenetic trees, networks, and population dynamics forward or backward in time with simple configuration setups.

- **Seamless integration with external CLI tools** 🧬  
  Easily pipe simulated trees into sequence simulators like [AliSim](https://iqtree.github.io/doc/AliSim), so setting up downstream sequence evolution takes only a single line.

- **Modular model design** 🧩  
  Combine event rules and rate functions seamlessly, and easily extend pre-built models or craft entirely custom architectures from scratch.

- **Arbitrary event rates** ⏱️  
  Apply constant, skyline, exponential, or arbitrary time-dependent rate functions, enhanced by customizable, model-dependent multipliers.

- **Flexible run controls** 🎛️  
  Enjoy complete flexibility over your simulations: set custom stopping conditions, time horizons, and acceptance criteria to generate tailored, high-quality datasets.

- **Parameter-driven dataset generation** 🎲  
  Define prior distributions over parameters to draw unique configurations for every dataset sample, and write flexible, in-line mathematical expressions directly inside your config file.

- **Automatic metadata management** 🗂️  
  Track sampled parameters, execution details, and custom log values automatically alongside your generated datasets for easy post-processing and result verification.

- **Multiprocessing support** ⚙️💻  
  Run independent simulations across worker processes, with a configurable worker count.

- **Plugin extensibility** 🔌  
  Package and register custom models and components as plugins that Phyloom can discover when running YAML configurations.

## ⚡️ Phyloom at a glance

<p align="center">
  <img src="https://raw.githubusercontent.com/gabriele-marino/phyloom/main/figures/pipeline.svg" alt="Phyloom's pipeline, from configuration to dataset" width="100%"/>
</p>

A single YAML file defines how many simulations to run, the model as a list of event rules and their hazards, the priors on the model parameters, when a simulation trial ends and whether it is kept. The configuration layer validates it and materializes one model per simulation trial by drawing from the priors; the simulator core runs that model under a common scheduler. The dataset pairs each output phylogeny (annotated trees or networks in extended Newick format) with metadata records holding the drawn parameter values. Phyloom offers a library of built-in models, and users can add new ones as plugins.

## 📦 Installation

Phyloom requires [Python](https://www.python.org/) 3.10+ to be installed on your system. There are several ways to install Python and managing different Python versions. One popular option is to use [uv](https://docs.astral.sh/uv/).

Once you have Python set up, you can install Phyloom directly from PyPI:

```bash
pip install phyloom
```

### 🛠️ Building from source

To get the latest development version, or to modify Phyloom itself, build it from source. First, clone the repository and move into it:

```bash
git clone https://github.com/gabriele-marino/phyloom.git
cd phyloom
```

Then, install it into your current Python environment with pip:

```bash
pip install .       # regular install
pip install -e .    # editable install: changes to the source code take effect without reinstalling
```

or [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uv sync                    # create the environment and install Phyloom and its dev tools
uv run pytest              # run the test suite
uv run phyloom examples/yaml/<config>.yaml  # run a configuration with your local version
```

## 🚀 Quick start

For a quick start, check out the bundled [examples](https://github.com/gabriele-marino/phyloom/tree/main/examples): every built-in model comes with a ready-to-run YAML configuration file in `examples/yaml/`, which defines the model, its parameters, and the dataset to generate, with no Python code needed. Pick your favorite config file and run Phyloom with:

```bash
phyloom examples/yaml/<config>.yaml
```

This command creates the output dataset in the folder defined by `output_dir` in the configuration file, with data directories and metadata for each dataset split.

## ⏱️ Benchmarks

Phyloom advances a simulation one event at a time. At each step, every event type proposes a firing time from its current number of opportunities, and the event that fires draws the lineages it acts on uniformly at random from an indexed set, in constant time. For a fixed set of event types, each step therefore costs constant time, independently of the population size, and a simulation of $m$ events runs in $O(m)$ time. All lineages are kept in memory until the end of the simulation, so that event rules and output hooks can query them, and since each event creates or ends at most a few lineages, memory is also $O(m)$.

What $m$ amounts to depends on the model. Forward-time models, such as birth-death and compartmental epidemics, simulate the full population, sampled and unsampled, so $m$ is proportional to the number of simulated lineages. When a simulation stops once $n$ tips are sampled and each lineage is sampled with probability $p$, this number scales as $n/p$, so both run time and memory grow linearly with $n$ and with $1/p$.

We evaluated this by generating trees with a growing number $n$ of sampled tips under a constant-rate birth-death model, in which infectious lineages branch at rate $\lambda = R_0\mu$ and are removed at rate $\mu = 0.4$, each removal being sampled with probability $p = 0.5$; $R_0 = \lambda/\mu = 3$ is the basic reproduction number. We compared Phyloom with [treesimulator](https://github.com/evolbioinfo/treesimulator), a pure-Python simulator that also simulates the full history:

<p align="center">
  <img src="https://raw.githubusercontent.com/gabriele-marino/phyloom/main/benchmarks/tree_size.svg" alt="Run time and memory against the number of sampled tips" width="80%"/>
</p>

<p align="center"><em>Wall-clock time (left) and peak memory (right) to generate a tree with a given number of sampled tips (mean ± s.d. over 5 replicates; log-log axes). The dashed line has slope 1, i.e. linear scaling, fitted to the Phyloom values. Benchmarks were run single-threaded on a MacBook with an Apple M3 chip and 16 GB RAM, with Python 3.10.</em></p>

The run time and memory of Phyloom grow close to linearly with $n$ (fitted log-log slopes of ~1.0), whereas the run time of treesimulator grows faster than linearly: Phyloom is about 3-fold faster at 500 tips and 9-fold faster at 4,000 tips. In exchange, Phyloom uses about 3-fold more memory, because each stored lineage is a full Python object that can be queried during and after the simulation. In practice, a tree costs roughly 0.07 ms and 8 kB per unit of $n/p$, so memory, not time, is the limiting factor: 16 GB of RAM allows $n/p$ up to about two million. This bounds the population, rather than the tree, that forward-time models can handle. Backward-time coalescent models instead simulate only the ancestry of the samples, so $m$ scales with the number of samples rather than with the population size, which makes them the better choice for sparsely sampled large populations.

### 🔁 Reproducing the benchmarks

Run from the repository root:

```bash
uv run --group benchmarks benchmarks/run.py
```

The benchmark script saves its measurements to `benchmarks/benchmarks.csv` and generates a plot at `benchmarks/benchmarks.svg`, while also printing key statistics to the console. Because pre-computed measurements are already included in the repository, running the script out-of-the-box will simply regenerate the plot and statistics from the existing CSV. To run a fresh benchmark on your own hardware, delete `benchmarks/benchmarks.csv` first. Note that exact execution times and memory usage will depend on your local hardware and environment.

## 📖 Examples and documentation

The repository comes with two folders of ready-to-run material:

- [`examples/`](https://github.com/gabriele-marino/phyloom/tree/main/examples) simulates classic models from macroevolution, phylodynamics, and population genetics (birth-death-sampling-hybridization models, the coalescent, and compartmental epidemics), each as a YAML configuration and as an equivalent Python script.
- [`plugins/`](https://github.com/gabriele-marino/phyloom/tree/main/plugins) contains complete, thoroughly commented plugin projects that add new models to Phyloom and make them available from YAML.

The [Phyloom documentation](https://gabriele-marino.github.io/phyloom/home) site provides a comprehensive reference detailing configuration options and models, with full Python API docs and user guides for YAML and Python.

## 📝 Paper

Phyloom is described in the preprint [*Phyloom: a flexible and extensible framework for simulating phylogenetic trees and networks* (Gabriele Marino, Daniele Silvestro, and Tanja Stadler)](https://github.com/gabriele-marino/phyloom/blob/main/paper/main.pdf).

## 📄 License

This project is licensed under [MIT License](https://github.com/gabriele-marino/phyloom/blob/main/LICENSE.txt).

## 📫 Contact

For questions, bug reports, or feature requests, consider opening an [issue on GitHub](https://github.com/gabriele-marino/phyloom/issues), or [contact me directly](mailto:gabmarino.8601@gmail.com). Please, don’t hesitate to reach out, I’m always happy to assist!
