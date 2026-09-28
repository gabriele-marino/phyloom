# ⏳🔀 Age-dependent branching (`phyloom-adb`)

A Phyloom plugin for binary **age-dependent branching** (ADB) processes with lineage states, selectable from YAML with `spec: adb`. It shows how to give every lineage its own clock with scheduled actions, and how to accept YAML expressions that depend on a lineage's state.

## 🧬 The model

In a binary age-dependent branching process, also known as a Bellman-Harris process, every individual lives for a random lifetime drawn from a general distribution. At the end of its life, it either dies or splits into two new individuals, which start their own lifetimes from age zero. This plugin simulates the multi-type version of the process:

1. Every lineage carries a discrete state, such as `A` or `B`.
2. When a lineage begins, it draws its lifetime from a distribution that depends on its state.
3. At the end of the lifetime, it dies with a state-dependent probability.
4. Otherwise, it is replaced by two descendants, whose states follow a configurable transition rule, and which start fresh lifetimes.

With non-exponential lifetimes, such as Gamma lifetimes with shape greater than one, the remaining lifetime of a lineage that has already lived for a while follows a different distribution than the lifetime of a newborn one. The chance that a lineage branches in the next instant therefore depends on its **age**.

Phyloom's events pair an event rule with a hazard: the rule counts the eligible lineages, and the hazard gives *each* of them the same rate, as a function of the global clock. Two lineages in the same state generally have different ages, so neither a rule nor a hazard can express an age-dependent rate. The model therefore keeps the clock on the lineage: when a lineage is created, the model draws its whole lifetime once and schedules an action, at the end of that lifetime, that resolves the lineage's fate.

## 📁 Files

Read the files in this order. Docstrings document the API; `#` comments walk through the design.

- [`src/phyloom_adb/model.py`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-adb/src/phyloom_adb/model.py): `ADBModel`, the runtime model: a `BDSHModel` subclass that schedules each lineage's end with `add_action` and resolves it with the BDSH primitives `finalize` (death) and `birth_from` (branching).
- [`src/phyloom_adb/expressions.py`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-adb/src/phyloom_adb/expressions.py): `FloatStateExpression` and `ChildStatesExpression`, expression types that can refer to the lineage's `state` and to the live `model`.
- [`src/phyloom_adb/adb.py`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-adb/src/phyloom_adb/adb.py): `ADBModelCfg`, the model configuration registered as `spec: adb`.
- [`examples/`](https://github.com/gabriele-marino/phyloom/tree/main/plugins/phyloom-adb/examples): runnable configurations with the dataset-generation settings, listed below.

## 💡 Examples

The [`examples/`](https://github.com/gabriele-marino/phyloom/tree/main/plugins/phyloom-adb/examples) folder holds runnable configurations. From the project folder, run any of them with:

```bash
uv sync
uv run phyloom examples/<config>.yaml
```

| Configuration | Description |
| --- | --- |
| [`ADB-multistate.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-adb/examples/ADB-multistate.yaml) | The initial lineage is in state `A` or `B`. Each lineage draws a Gamma lifetime with a state-specific shape and scale, and dies at the end of it with a state-specific probability; otherwise, each of its two descendants independently draws its state from the transition row of its parent's state |
