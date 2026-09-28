<p align="center">
  <img src="https://raw.githubusercontent.com/gabriele-marino/phyloom/main/logo.svg" alt="Phyloom" width="620"/>
</p>

---

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/phyloom?style=flat-square&color=2A9D8F)](https://pypi.org/project/phyloom/)
[![Documentation](https://img.shields.io/badge/docs-website-6F42C1?style=flat-square)](https://gabriele-marino.github.io/phyloom/home)

[Phyloom](https://github.com/gabriele-marino/phyloom) is a flexible Python framework for designing and running stochastic phylogenetic tree and network simulators with minimal boilerplate. By handling core network/tree construction, the simulation loop, and data pipelines under the hood, Phyloom lets you focus directly on defining your biological models.

You can work with pre-built model families, extend existing ones with custom event rules and rate functions, or implement brand-new models from scratch, all fully configurable via YAML or the Python API. Out of the box, Phyloom supports:

- **Birth-death-sampling-hybridization (BDSH)** models for forward-in-time branching processes with unbounded population growth, lineage sampling, and reticulation;
- **Coalescent models** to trace population ancestry backward in time;
- **Compartment-based epidemic models** for simulating the spread of infectious diseases in structured populations (such as SIR, SEIR and SEIRS).

## ✨ Features

Phyloom comes packed with features, including:

- **Effortless tree and network simulation** 🌳🕸️  
  Simulate complex phylogenetic trees, networks, and population dynamics forward or backward in time with simple configuration setups.

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

## 📦 Installation

Phyloom requires [Python](https://www.python.org/) 3.10+ to be installed on your system. There are several ways to install Python and managing different Python versions. One popular option is to use [uv](https://docs.astral.sh/uv/).

Once you have Python set up, you can install Phyloom directly from PyPI:

```bash
pip install phyloom
```

Or install from source:

```bash
git clone https://github.com/gabriele-marino/phyloom.git
cd phyloom
pip install .
```

## 🚀 Quick start

For a quick start, check out the bundled [examples](https://github.com/gabriele-marino/phyloom/tree/main/examples): every built-in model example comes as a [YAML configuration](https://github.com/gabriele-marino/phyloom/tree/main/examples/yaml) and as an equivalent [Python script](https://github.com/gabriele-marino/phyloom/tree/main/examples/python), and the [plugin projects](https://github.com/gabriele-marino/phyloom/tree/main/plugins) show how to add your own custom models and make them available from YAML.  

Pick your favorite config file and run Phyloom with:

```bash
phyloom path/to/config.yaml
```

This command creates the output dataset in your configured folder, setting up data directories and metadata files for every split automatically.   

## 📖 Examples and documentation

The [Phyloom documentation](https://gabriele-marino.github.io/phyloom/home) site provides a comprehensive reference detailing configuration options, models, and usage examples. It includes full Python API docs as well as step-by-step tutorials for building custom plugins and extending the framework.

## 📄 License

This project is licensed under [MIT License](https://github.com/gabriele-marino/phyloom/blob/main/LICENSE.txt).

## 📫 Contact

For questions, bug reports, or feature requests, consider opening an [issue on GitHub](https://github.com/gabriele-marino/phyloom/issues), or [contact me directly](mailto:gabmarino.8601@gmail.com). Please, don’t hesitate to reach out, I’m always happy to assist!
