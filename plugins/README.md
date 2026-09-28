# 🔌 Plugins

A plugin is an installable Python package that extends Phyloom with new functionality, such as a model or event rules, and registers it so that it can be used in YAML configurations. Once a plugin is installed, the `phyloom` command runs its configurations with all the usual machinery: parameter priors, stopping and acceptance criteria, parallel sample generation, logs, and output hooks. The [Python user guide](https://gabriele-marino.github.io/phyloom/user_guide/python.html#plugins) explains how to write a plugin from scratch; the example projects below, in the [`plugins/`](https://github.com/gabriele-marino/phyloom/tree/main/plugins) folder of the repository, are complete, thoroughly commented, and ready-to-use project examples.

| Project | Model |
| --- | --- |
| [`⏳🔀 phyloom-adb`](https://github.com/gabriele-marino/phyloom/tree/main/plugins/phyloom-adb) | Age-dependent branching: lineages with non-exponential, state-dependent lifetimes that die or split at the end of their lives |
| [`🦠🕵️ phyloom-ct`](https://github.com/gabriele-marino/phyloom/tree/main/plugins/phyloom-ct) | Contact tracing: an epidemic in which sampled individuals trigger the sampling of their transmission contacts |

Each project's README introduces its model, maps its files, and lists its example configurations. The code is commented as a walkthrough, meant to be read from top to bottom.

## 🙋‍♂️ When to write a plugin

Start from YAML: the built-in models, combined with event rules, hazards, rate multipliers, scheduled actions, and stop hooks, already cover a wide range of processes (see the [examples](https://github.com/gabriele-marino/phyloom/tree/main/examples)). A plugin is needed when a process requires something these pieces cannot express, such as state that belongs to individuals (identities, contact histories, or ages), waiting times that belong to a single lineage (non-exponential lifetimes), or events that trigger other events depending on the model's history (tracing the contacts of a sampled individual). If you only need a custom process for your own analysis, you can also drive the Python API from a script, without a plugin: a plugin is just the way to make it available to others through YAML configurations.

## 🚀 Setting up and running a plugin

You need Python 3.10 or later and [uv](https://docs.astral.sh/uv/getting-started/installation/). Clone the repository, move into the project of a plugin, and run one of its example configurations:

```bash
git clone https://github.com/gabriele-marino/phyloom.git
cd phyloom/plugins/<project>
uv sync
uv run phyloom examples/<config>.yaml
```

`uv sync` installs Phyloom and the plugin into the project's environment, and `uv run` runs the `phyloom` command from it. The dataset is written to the `output_dir` set in the configuration.

## 📁 Project layout

Each plugin is a Python package with a `pyproject.toml` file, a `src/` folder with the runtime model and its configuration classes, and an `examples/` folder with runnable YAML configurations. The layout is:

```text
phyloom-<name>/
├── pyproject.toml     # package metadata, the Phyloom dependency, and the plugin entry point
├── uv.lock            # exact dependency versions resolved by uv
├── .python-version    # Python version used by uv
├── README.md          # the model, a map of the files, and a table of the examples
├── examples/          # runnable YAML configurations
└── src/
    └── phyloom_<name>/
        ├── __init__.py
        ├── py.typed   # marks the package as typed
        └── ...        # the runtime model and its configuration classes
```

In `pyproject.toml`, the `phyloom.plugins` entry points name the modules that register the plugin's configuration classes, and the `[tool.uv.sources]` table installs Phyloom from the local copy of the repository, so the plugins always run against the current source.
