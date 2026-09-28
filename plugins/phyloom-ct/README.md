# 🦠🕵️ Contact tracing (`phyloom-ct`)

A Phyloom plugin for epidemics with **contact tracing**, selectable from YAML with `spec: ct`. The model remembers who infected whom, and when an individual is sampled, its transmission contacts can be notified and sampled at the same time. It shows how to keep per-individual state consistent while lineages are replaced, and how to write custom event rules.

## The model

Infected individuals are lineages, each in a state, such as exposed or infectious. They transmit, creating new infected individuals, change state, and leave either unobserved or by being **sampled**, for example through a positive test. Which states exist, and which transitions are possible between them, is set by the events of the configuration. Contact tracing adds a response to each sample. The sampled individual becomes an **index case**, and its contacts are traced:

1. The contacts of an individual are the one that infected it and the individuals it infected, taken from most recent to least recent.
2. Only the first `max_notifications` contacts in that order are considered, or all of them if the limit is `null`.
3. Each considered contact that is still infected is independently notified with probability `notification_probability`.
4. A notified contact is sampled and removed at the same moment as the index case. Its own contacts are **not** traced further.

Samples therefore arrive in clusters of linked individuals with identical sampling times, and individuals in states that are never sampled directly, such as exposed individuals, can appear as tips once they are traced. Such data is useful for studying how tracing distorts phylodynamic inference, or for training methods that account for it.

`CTModel` extends `BDSHModel`, which already tracks the lineages, their times, and which ones are active or sampled. Because a lineage is replaced on every transmission or state change, it cannot identify a person for long, so the model gives each individual a stable id, maps it to its current lineage, and records its contacts. All changes go through three new primitives, `transmission`, `migration`, and `recovery`, which call the BDSH primitives and update the individual bookkeeping at the same time. Calling the BDSH primitives directly would leave the individuals out of date, which is why the plugin has its own event rules. Rates need no extra machinery: each transition has a per-individual rate set by the individual's state, as in any stochastic event. Tracing has no rate of its own; it happens inside a sampled recovery.

## 📁 Files

Read the files in this order. Docstrings document the API; `#` comments walk through the design.

- [`src/phyloom_ct/model.py`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-ct/src/phyloom_ct/model.py): `CTModel`, the runtime model: a `BDSHModel` subclass with the individual bookkeeping and the primitives `transmission`, `migration`, and `recovery`.
- [`src/phyloom_ct/events.py`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-ct/src/phyloom_ct/events.py): the `Transmission`, `Migration`, and `Recovery` event rules, one per primitive.
- [`src/phyloom_ct/ct.py`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-ct/src/phyloom_ct/ct.py): the configuration layer: a dedicated event-rule registry, one configuration class per rule, and `CTModelCfg`, registered as `spec: ct`.
- [`examples/`](https://github.com/gabriele-marino/phyloom/tree/main/plugins/phyloom-ct/examples): runnable configurations with the dataset-generation settings, listed under below.

## 💡 Examples

The [`examples/`](https://github.com/gabriele-marino/phyloom/tree/main/plugins/phyloom-ct/examples) folder holds runnable configurations. From the project folder, run any of them with:

```bash
uv sync
uv run phyloom examples/<config>.yaml
```

| Configuration | Description |
| --- | --- |
| [`BDEI-CT.yaml`](https://github.com/gabriele-marino/phyloom/blob/main/plugins/phyloom-ct/examples/BDEI-CT.yaml) | BDEI model with the BDSH rules replaced by their contact-tracing counterparts and two tracing parameters added: each index case considers at most five contacts, each notified with a probability drawn per sample |
