# 🐍 Python user guide

Phyloom's Python API gives you programmatic access to everything the YAML interface does, and to everything it is built on. Use it to work with trees, networks, and alignments; to run simulations directly from code; and to extend Phyloom with new event rules, hazards, and models that then become available to YAML configurations. For declarative configuration files, see the [YAML user guide](yaml). This guide describes the concepts and contracts behind each extension point; complete, runnable projects built on them are collected in the [plugins](../plugins) section.

## 📍 API overview

Phyloom is split into three layers:

| Layer | Package | Responsibility |
| --- | --- | --- |
| Data structures | {py:mod}`phyloom.core`, {py:mod}`phyloom.io` | Trees, networks, and sequence alignments, and reading and writing them. |
| Simulator | {py:mod}`phyloom.simulator` | The runtime objects that actually simulate: models, events, event rules, and hazards. |
| Configuration | {py:mod}`phyloom.configs` | [Pydantic](https://docs.pydantic.dev/) models that validate configuration data (such as a parsed YAML file) and build simulator objects from it. |

The simulator and configuration layers are kept separate on purpose. A simulator object is live, mutable state: a model owns its clock, random number generator, and current lineages. A configuration object is an immutable, validated *description* of how to build one. The bridge between the two is the `contextualize(context)` method that every configuration class implements: given a **materialized context** (the dictionary of sample-specific values drawn from the `context` block of a configuration), it returns a fresh simulator object. This is what lets one configuration produce many independent simulations, each with its own parameter draws and random seed.

Every extension point therefore comes in two parts: a runtime class that implements the behavior, and a configuration class that is registered under a `spec` key so that configuration data can select it.

| To add | Runtime base class: methods to implement | Configuration base class: methods to implement | Register in |
| --- | --- | --- | --- |
| An event rule | {py:class}`EventRule <phyloom.simulator.core.EventRule>`: {py:meth}`opportunities <phyloom.simulator.core.EventRule.opportunities>`, {py:meth}`apply <phyloom.simulator.core.EventRule.apply>`<br>or, for a {py:class}`NetModel <phyloom.simulator.net.NetModel>`:<br>{py:class}`LineageEventRule <phyloom.simulator.net.LineageEventRule>`: {py:meth}`apply_to_lineage <phyloom.simulator.net.LineageEventRule.apply_to_lineage>`<br>{py:class}`LineagePairEventRule <phyloom.simulator.net.LineagePairEventRule>`: {py:meth}`apply_to_lineages <phyloom.simulator.net.LineagePairEventRule.apply_to_lineages>` | {py:class}`EventRuleCfg <phyloom.configs.core.EventRuleCfg>`: {py:meth}`contextualize <phyloom.configs.core.EventRuleCfg.contextualize>` | The target model's event-rule registry |
| A hazard | {py:class}`Hazard <phyloom.simulator.hazards.Hazard>`: {py:meth}`invert <phyloom.simulator.hazards.Hazard.invert>` | {py:class}`HazardCfgBase <phyloom.configs.hazards.HazardCfgBase>`: {py:meth}`contextualize <phyloom.configs.hazards.HazardCfgBase.contextualize>` | {py:data}`HAZARD_REGISTRY <phyloom.configs.hazards.HAZARD_REGISTRY>` |
| A model | {py:class}`Model <phyloom.simulator.core.Model>`<br>or {py:class}`NetModel <phyloom.simulator.net.NetModel>`: {py:meth}`get_root <phyloom.simulator.net.NetModel.get_root>`, {py:attr}`origin <phyloom.simulator.net.NetModel.origin>`, {py:meth}`time_of <phyloom.simulator.net.NetModel.time_of>` | {py:class}`ModelCfgBase <phyloom.configs.core.ModelCfgBase>`: {py:meth}`contextualize <phyloom.configs.core.ModelCfgBase.contextualize>` | {py:data}`MODEL_REGISTRY <phyloom.configs.core.MODEL_REGISTRY>` |

## 📦 Core data structures

Phyloom provides data structures for trees and networks, which represent phylogenetic histories, and for sequence alignments. They are defined in {py:mod}`phyloom.core`, and {py:mod}`phyloom.io` reads and writes them in the Newick and FASTA formats. Because they are independent of the simulator, they can also be used to analyze data produced by other tools.

### 🏷️ Nodes, edges, and metadata

Phylogenetic histories are directed graphs built from {py:class}`Node <phyloom.core.Node>` and {py:class}`Edge <phyloom.core.Edge>` records. A node has a name; an edge has an optional, non-negative length. Both accept arbitrary keyword arguments as **metadata**, which you can read and update with item syntax or with the {py:class}`MetadataMixin <phyloom.utils.MetadataMixin>` methods (`get`, `set`, `update`, `delete`, `clear`):

```{doctest}
>>> from phyloom.core import Edge, Node
>>> node = Node("x", label="u")
>>> node.name, node["label"]
('x', 'u')
>>> node["score"] = 1.5
>>> node.update({"label": "v"})
>>> dict(node.metadata)
{'label': 'v', 'score': 1.5}
>>> edge = Edge(0.5, support=0.9)
>>> edge.length, edge.get("support"), edge.get("missing", "default")
(0.5, 0.9, 'default')
```

`metadata` is a read-only view: modify it through the methods above rather than by assigning to it.

### 🌳 Trees and networks

A {py:class}`Net <phyloom.core.Net>` is a rooted directed acyclic graph: every node is reachable from the root, and edges point away from it. A node may have several parents, which represents a **reticulation** (for example hybridization or recombination). A {py:class}`Tree <phyloom.core.Tree>` is a `Net` in which every node except the root has exactly one parent, and it adds tree-specific methods.

Both are built from a mapping of integer node ids to nodes, a mapping of `(parent, child)` id pairs to edges, the root id, and an optional **stem** edge leading into the root from above. The structure is validated on construction: cycles, nodes unreachable from the root, and (for trees) nodes with several parents are rejected.

```{doctest}
>>> from phyloom.core import Edge, Net, Node, Tree
>>> nodes = {
...     0: Node("root"),
...     1: Node("x"),
...     2: Node("y"),
...     3: Node("a"),
...     4: Node("b"),
...     5: Node("c"),
... }
>>> edges = {
...     (0, 1): Edge(1.0),
...     (0, 2): Edge(2.0),
...     (1, 3): Edge(0.5),
...     (1, 4): Edge(0.5),
...     (2, 5): Edge(1.5),
... }
>>> tree = Tree(nodes, edges, root=0, stem=Edge(0.1))
>>> tree
Tree(n_nodes=6, n_edges=5)
>>> tree.pretty_print()
root [0.1]
|-- x [1.0]
|   |-- a [0.5]
|   `-- b [0.5]
`-- y [2.0]
    `-- c [1.5]
```

Nodes are referred to by id throughout the API. The {py:attr}`nodes <phyloom.core.Net.nodes>` and {py:attr}`edges <phyloom.core.Net.edges>` properties map ids back to records, and {py:meth}`get_node_id <phyloom.core.Net.get_node_id>` and {py:meth}`get_node <phyloom.core.Net.get_node>` look nodes up by name. Iterating over a tree or network yields node ids in topological order: every parent comes before its children.

```{doctest}
>>> [tree.nodes[i].name for i in tree]
['root', 'y', 'c', 'x', 'b', 'a']
>>> tree.children_of(0), tree.parents_of(3)
((1, 2), (1,))
>>> tree.get_leaves(), tree.count_leaves()
((5, 4, 3), 3)
>>> tree.get_internals(), tree.is_leaf(0), tree.is_internal(0)
((0, 2, 1), False, True)
>>> tree.get_node_id("a"), tree.get_node("a")
(3, Node(name='a', metadata={}))
>>> tree.edges[(0, 2)].length
2.0
```

Trees additionally provide parent lookup, branch lengths, common ancestors, and paths:

```{doctest}
>>> tree.parent_of(3)
1
>>> tree.edge_length_of(3), tree.edge_length_of(0)  # the root's length is its stem's
(0.5, 0.1)
>>> tree.is_binary()
False
>>> tree.get_mrca([3, 4]), tree.get_mrca([3, 5])
(1, 0)
>>> tree.get_path(3, 5)
[3, 1, 0, 2, 5]
>>> tree.ladderize()  # in place: children with fewer descendant leaves come first
>>> tree.children_of(0)
(2, 1)
>>> tree.pretty_print()
root [0.1]
|-- y [2.0]
|   `-- c [1.5]
`-- x [1.0]
    |-- a [0.5]
    `-- b [0.5]
```

The same navigation methods work on networks, where a node can list several parents. In the printed view, the second occurrence of a reticulation node is shown as a reference rather than repeated:

```{doctest}
>>> nodes = {i: Node(name) for i, name in enumerate(["root", "x", "y", "h"])}
>>> edges = {(0, 1): Edge(), (0, 2): Edge(), (1, 3): Edge(), (2, 3): Edge()}
>>> net = Net(nodes, edges, root=0)
>>> net.parents_of(3)
(1, 2)
>>> net.pretty_print()
root
|-- x
|   `-- h
`-- y
    `-- ref h
```

Trees and networks are read-only once constructed, except for {py:meth}`ladderize <phyloom.core.Tree.ladderize>`, which only reorders children.

### 💾 Newick input and output

Phyloom uses Newick as its standard format for trees and networks. Newick is a compact, text-based format in which nested parentheses describe the branching structure:

- Parentheses group the children of a node, and commas separate siblings.
- A label after a node (or after its closing parenthesis) names it.
- A value after `:` gives the length of the edge leading into the node.
- Bracketed key-value comments such as `[&key=value,other=1.5]` store metadata. Metadata directly after a node label belongs to that node; metadata after an edge length (or after a bare `:`) belongs to that edge. Values are parsed as Python literals when possible and kept as strings otherwise.
- In networks, a label prefixed with `#` marks a reticulation node. Every occurrence of the same `#` label refers to the same node, so the node gains one parent for each occurrence.
- A semicolon ends each tree or network. Files contain one Newick string per line.

The full grammar is documented in {py:mod}`phyloom.io.newick`. {py:func}`io.from_newick <phyloom.io.newick.from_newick>` parses a string into a `Net` by default, or into a `Tree` with `parse_as="tree"`; {py:func}`io.to_newick <phyloom.io.newick.to_newick>` (also available as the {py:meth}`Net.to_newick <phyloom.core.Net.to_newick>` method) serializes one back. Parsed node ids are assigned in the order nodes appear in the string.

```{doctest}
>>> from phyloom.io import from_newick, to_newick
>>> net = from_newick("((a:1.0,#h:0.5)x:1.0,(#h:0.2,b:1.0)y:1.0)root;")
>>> net.pretty_print()
root
|-- x [1.0]
|   |-- a [1.0]
|   `-- h [0.5]
`-- y [1.0]
    |-- ref h [0.2]
    `-- b [1.0]
>>> [net.nodes[p].name for p in net.parents_of(net.get_node_id("h"))]
['x', 'y']
>>> tree = from_newick("((a:1,b:2)x[&kind='clade']:0.5[&support=0.9],c:3)root;", parse_as="tree")
>>> x = tree.get_node_id("x")
>>> dict(tree.nodes[x].metadata), dict(tree.edges[(tree.parent_of(x), x)].metadata)
({'kind': 'clade'}, {'support': 0.9})
>>> to_newick(tree)
'((a:1.0,b:2.0)x[&kind="clade"]:0.5[&support=0.9],c:3.0)root;'
```

For files, {py:func}`dump_newick <phyloom.io.newick.dump_newick>` writes an iterable of trees or networks, one per line, and {py:func}`load_newick <phyloom.io.newick.load_newick>` lazily yields them back. The {py:meth}`Net.dump <phyloom.core.Net.dump>` method writes a single tree or network:

```python
from phyloom.io import dump_newick, load_newick

dump_newick([tree, net], "histories.nwk")
tree.dump("tree.nwk")

nets = list(load_newick("histories.nwk"))  # Net objects
trees = list(load_newick("tree.nwk", load_as="tree"))  # Tree objects
```

### 🧬 Sequence alignments and FASTA

A {py:class}`SequenceRecord <phyloom.core.SequenceRecord>` stores a named, non-empty character sequence with optional metadata, and an {py:class}`MSA <phyloom.core.MSA>` (multiple sequence alignment) is an ordered collection of records that must all have the same length:

```{doctest}
>>> from phyloom.core import MSA, SequenceRecord
>>> msa = MSA([
...     SequenceRecord("a", "ACGT", group="u"),
...     SequenceRecord("b", "A-GT", group="v"),
...     SequenceRecord("c", "ACGT", group="u"),
... ])
>>> msa.shape, msa.n_unique_sequences
((3, 4), 2)
>>> [(record.name, record.chars, record["group"]) for record in msa]
[('a', 'ACGT', 'u'), ('b', 'A-GT', 'v'), ('c', 'ACGT', 'u')]
```

Alignments are read and written in FASTA, where each record starts with a `>` header line followed by one or more lines of sequence characters. Headers often pack several fields together, for example `>name|field1|field2`. {py:func}`load_fasta <phyloom.io.fasta.load_fasta>` uses the whole header as the sequence name unless you pass functions that split it into a name and metadata, and {py:func}`dump_fasta <phyloom.io.fasta.dump_fasta>` accepts the inverse function to rebuild headers:

```python
from phyloom.io import dump_fasta, load_fasta

msa = load_fasta(
    "alignment.fasta",
    sequence_name_from_header=lambda header: header.split("|")[0],
    sequence_metadata_from_header=lambda header: {"group": header.split("|")[1]},
)
dump_fasta(
    msa,
    "alignment-copy.fasta",
    header_from_sequence=lambda record: f"{record.name}|{record['group']}",
)
```

## 🧱 Root configuration types

Configuration classes declare the parameters they accept as [Pydantic](https://docs.pydantic.dev/) fields. The field types come from {py:mod}`phyloom.configs.roots`, which provides **root configuration types**: Pydantic root models that wrap a single raw value, validate it, and resolve it against the materialized context in their own `contextualize(context)` method. They are the building blocks of every configuration class, whether it configures an event rule, a hazard, a model, or the runner, and they are what lets a parameter be a literal, refer to context variables, or be computed from them.

| Type | Resolves to | Accepts |
| --- | --- | --- |
| {py:class}`StrCfg <phyloom.configs.roots.StrCfg>`, {py:class}`StrPairCfg <phyloom.configs.roots.StrPairCfg>` | {py:class}`str`, {py:class}`tuple`\[{py:class}`str`, {py:class}`str`\] | Strings with `{name}` placeholders filled from the context. |
| {py:class}`IntCfg <phyloom.configs.roots.IntCfg>`, {py:class}`FloatCfg <phyloom.configs.roots.FloatCfg>` | {py:class}`int`, {py:class}`float` | NumPy expressions over context variables. |
| {py:class}`FloatSequenceCfg <phyloom.configs.roots.FloatSequenceCfg>` | {py:class}`Sequence <collections.abc.Sequence>`\[{py:class}`float`\] | A list of float expressions, or one expression returning an array. |

```{doctest}
>>> from phyloom.configs.roots import (
...     FloatCfg,
...     FloatSequenceCfg,
...     IntCfg,
...     StrCfg,
...     StrPairCfg,
... )
>>> context = {"init_state": "A", "base_rate": 0.5, "n": 3}
>>> StrCfg.model_validate("{init_state}").contextualize(context)
'A'
>>> StrPairCfg.model_validate(["{init_state}", "B"]).contextualize(context)
('A', 'B')
>>> IntCfg.model_validate("np.sum([1, 2, n])").contextualize(context)
6
>>> FloatCfg.model_validate("2 * base_rate").contextualize(context)
1.0
>>> FloatSequenceCfg.model_validate(["base_rate", "2 * base_rate"]).contextualize(context)
[0.5, 1.0]
>>> FloatSequenceCfg.model_validate("base_rate * np.arange(1, n + 1)").contextualize(context)
[0.5, 1.0, 1.5]
```

Plain annotations such as {py:class}`bool` or {py:class}`str` also work for values that should never depend on the context, and {py:obj}`None` defaults make fields optional: {py:func}`contextualize_optional <phyloom.configs.utils.contextualize_optional>` resolves an optional field while preserving {py:obj}`None`.

### 📝 Source configurations

Root types that hold Python source code derive from one of two bases: {py:class}`ExpressionCfg <phyloom.configs.roots.ExpressionCfg>` for a single expression that produces a value, and {py:class}`StatementCfg <phyloom.configs.roots.StatementCfg>` for statements run for their side effects. The source is syntax-checked when the configuration is validated, so a typo fails early with a {py:exc}`ValidationError <pydantic_core.ValidationError>`, and it is run later, during the simulation, in a namespace that contains the materialized context, {py:mod}`numpy` as `np`, and any names bound by the concrete type. Source is ordinary Python run with {py:func}`eval` or {py:func}`exec`, so configuration input must be trusted.

Phyloom's own source types differ only in how the source is run and in which names they bind:

| Type | Base | Resolves to | Binds |
| --- | --- | --- | --- |
| {py:class}`NumPyExpressionCfg <phyloom.configs.roots.NumPyExpressionCfg>` | {py:class}`ExpressionCfg <phyloom.configs.roots.ExpressionCfg>` | The evaluated value | Nothing beyond the context and `np` |
| {py:class}`NonNegativeTimeFnCfg <phyloom.configs.roots.NonNegativeTimeFnCfg>` | {py:class}`ExpressionCfg <phyloom.configs.roots.ExpressionCfg>` | {py:class}`Callable <collections.abc.Callable>`\[\[{py:class}`float`\], {py:class}`float`\], rejecting negative values | The simulated time `t` |
| {py:class}`ModelExpressionCfg <phyloom.configs.roots.ModelExpressionCfg>` | {py:class}`ExpressionCfg <phyloom.configs.roots.ExpressionCfg>` | {py:class}`Callable <collections.abc.Callable>`\[\[{py:class}`Model <phyloom.simulator.core.Model>`\], {py:class}`object`\] | The current `model` |
| {py:class}`ModelNonNegativeFloatCfg <phyloom.configs.roots.ModelNonNegativeFloatCfg>` | {py:class}`ExpressionCfg <phyloom.configs.roots.ExpressionCfg>` | {py:class}`Callable <collections.abc.Callable>`\[\[{py:class}`Model <phyloom.simulator.core.Model>`\], {py:class}`float`\], rejecting negative values | The current `model` |
| {py:class}`ModelPredicateCfg <phyloom.configs.roots.ModelPredicateCfg>` | {py:class}`ExpressionCfg <phyloom.configs.roots.ExpressionCfg>` | {py:class}`Callable <collections.abc.Callable>`\[\[{py:class}`Model <phyloom.simulator.core.Model>`\], {py:class}`bool`\] | The current `model` |
| {py:class}`ModelActionCfg <phyloom.configs.roots.ModelActionCfg>` | {py:class}`StatementCfg <phyloom.configs.roots.StatementCfg>` | {py:class}`Callable <collections.abc.Callable>`\[\[{py:class}`Model <phyloom.simulator.core.Model>`\], {py:obj}`None`\] | The current `model` |

When a parameter needs other bindings or another result type, subclass the base that matches the source and implement `contextualize(context)`. A source usually depends on simulation state that only exists later, such as the current model, so `contextualize` should not run the source itself: it should return a function that captures `context` and runs the source each time it is called. Keyword arguments passed to the run methods become names in the source's namespace, taking precedence over context names and `np`:

- {py:meth}`ExpressionCfg.evaluate_typed(context, typeguard, **bindings) <phyloom.configs.roots.ExpressionCfg.evaluate_typed>` evaluates the expression, converts NumPy results to plain Python values, and raises an error unless the value passes a typeguard from {py:mod}`phyloom.configs.roots.typeguards`, such as {py:data}`BOOL_TG <phyloom.configs.roots.typeguards.BOOL_TG>`, {py:data}`INT_TG <phyloom.configs.roots.typeguards.INT_TG>`, {py:data}`FLOAT_TG <phyloom.configs.roots.typeguards.FLOAT_TG>`, or {py:data}`FLOAT_SEQUENCE_TG <phyloom.configs.roots.typeguards.FLOAT_SEQUENCE_TG>`, or your own {py:class}`NamedTypeguard <phyloom.configs.roots.typeguards.NamedTypeguard>`. Prefer it for numbers, booleans, and sequences of them;
- {py:meth}`ExpressionCfg.evaluate(context, **bindings) <phyloom.configs.roots.ExpressionCfg.evaluate>` evaluates the expression and returns its raw value, for results that a typeguard cannot describe;
- {py:meth}`StatementCfg.execute(context, **bindings) <phyloom.configs.roots.StatementCfg.execute>` runs the statements.

A typeguard checks the type only, so add explicit checks for constraints such as non-negativity, and raise a {py:exc}`ValueError` that names the source. For example, a rate that depends on both the model and a lineage state:

```python
from collections.abc import Callable
from typing import Any

from phyloom.configs.roots import ExpressionCfg
from phyloom.configs.roots.typeguards import FLOAT_TG
from phyloom.types import Context


class StateRateCfg(ExpressionCfg):
    def contextualize(self, context: Context) -> Callable[[Any, str], float]:
        def rate(model: Any, state: str) -> float:
            value = self.evaluate_typed(context, FLOAT_TG, model=model, state=state)
            if value < 0:
                raise ValueError(f"Expression {self.root!r} evaluated to {value} < 0.")
            return value

        return rate
```

Used as the type of a field, it accepts expressions of `model`, `state`, and the context:

```yaml
state_rate: base_rate * (2.0 if state == "B" else 1.0) * np.exp(-decay * model.current_time)
```

## 🎲 Stochastic events

A stochastic {py:class}`Event <phyloom.simulator.core.Event>` combines three independent pieces:

- an {py:class}`EventRule <phyloom.simulator.core.EventRule>`, which defines *what* happens: which transitions are currently possible in the model, and how one of them changes the model;
- a {py:class}`Hazard <phyloom.simulator.hazards.Hazard>`, which defines *when* it happens: the instantaneous, time-dependent rate $\lambda(t)$ at which each possible transition fires;
- an optional **rate multiplier**, a function of the current model state that scales the overall rate.

At every simulation step, the event asks its rule for the number of eligible **opportunities** $c$, evaluates the multiplier $m$ (1 if absent), draws $E \sim \operatorname{Exponential}(1)$, and asks the hazard for the earliest time $t$ at which $c \cdot m \cdot H(t_0, t) = E$, where $H(t_0, t) = \int_{t_0}^{t} \lambda(s)\,\mathrm{d}s$ is the cumulative hazard from the current time $t_0$. The model then applies whichever events or scheduled actions are due first. If $c = 0$, $m = 0$, or the threshold is never reached, the event proposes no time and cannot fire in that step. The [fundamentals](../fundamentals) page explains this scheme in depth.

Pass events to a {py:class}`Model <phyloom.simulator.core.Model>` through its `events` argument, or add them to a running model with {py:meth}`add_event <phyloom.simulator.core.Model.add_event>`.

(python-event-rules)=

### 📜 Event rules

An event rule is written for a particular model type, because it reads and changes that model's state. Phyloom provides built-in rules for each model family (see {ref}`built-in models <python-built-in-models>`); a new rule implements the {py:class}`EventRule <phyloom.simulator.core.EventRule>` protocol, which has two methods:

- **{py:meth}`opportunities(model) -> int <phyloom.simulator.core.EventRule.opportunities>`** returns the number of elementary transitions currently available, such as the number of eligible lineages or eligible lineage pairs. Each opportunity fires at the per-opportunity rate given by the hazard, so the total rate of the event is proportional to this count. Returning `0` makes the event inactive. The method is called at every simulation step and **must not modify the model**.
- **{py:meth}`apply(model) <phyloom.simulator.core.EventRule.apply>`** performs exactly one of the eligible transitions, typically by drawing one opportunity uniformly at random and mutating the model in place. It is called when the event fires.

A rule receives its parameters (for example, which states it applies to) in its constructor and should otherwise be stateless: the model is the single source of truth, and the same rule instance is queried at every step.

```python
from phyloom.simulator.core import EventRule, Model


class MyModel(Model): ...


class MyEventRule(EventRule[MyModel]):
    def __init__(self, param: str):
        self._param = param

    def opportunities(self, model: MyModel) -> int:
        # Count eligible transitions without changing the model.
        ...

    def apply(self, model: MyModel) -> None:
        # Draw one eligible transition with model.rng and apply it.
        ...
```

Use {py:attr}`model.rng <phyloom.simulator.core.Model.rng>` for every random choice in {py:meth}`apply <phyloom.simulator.core.EventRule.apply>`. It is the model's seeded generator, so using it keeps simulations reproducible.

```{note}
Events whose proposed times coincide exactly, as happens with immediate (`delta`) hazards or with a scheduled action due at the same time, are applied one after another in random order. An {py:meth}`apply <phyloom.simulator.core.EventRule.apply>` method can therefore see a state already changed by another transition at the same time. Rules that may fire simultaneously with others should tolerate this, for example by returning early when no opportunity remains.
```

For models that build lineage networks ({py:class}`NetModel <phyloom.simulator.net.NetModel>` subclasses), two base classes implement the counting and uniform drawing for the most common cases, so that only the transition itself remains to be written:

- {py:class}`LineageEventRule <phyloom.simulator.net.LineageEventRule>` targets one active lineage, optionally restricted to a state. Implement {py:meth}`apply_to_lineage(model, lineage) <phyloom.simulator.net.LineageEventRule.apply_to_lineage>`.
- {py:class}`LineagePairEventRule <phyloom.simulator.net.LineagePairEventRule>` targets a pair of distinct active lineages, optionally restricted to a pair of states. Unordered pairs are counted within one state, ordered pairs across two states. Implement {py:meth}`apply_to_lineages(model, lineages) <phyloom.simulator.net.LineagePairEventRule.apply_to_lineages>`.

```python
from phyloom.simulator.net import LineageEventRule, NetModel
from phyloom.types import NodeID


class MyNetModel(NetModel): ...


class MyLineageRule(LineageEventRule[MyNetModel]):
    def apply_to_lineage(self, model: MyNetModel, lineage: NodeID) -> None:
        # Change the selected lineage through the model's primitives.
        ...


rule = MyLineageRule(state="S")  # only lineages in state "S" are eligible
```

To make a rule available in configuration data, subclass {py:class}`EventRuleCfg <phyloom.configs.core.EventRuleCfg>`, parametrized by the target model type. Its Pydantic fields declare the parameters accepted in configuration data, typically with root configuration types, and its {py:meth}`contextualize(context) <phyloom.configs.core.EventRuleCfg.contextualize>` method resolves those fields against the materialized context and returns a new runtime rule. Unknown fields are rejected during validation.

Register the class in the target model's event-rule registry under the `spec` key that configuration data will use. The built-in models expose theirs as `BDSH_EVENT_RULE_REGISTRY`, `COALESCENT_EVENT_RULE_REGISTRY`, and `EPIDEMIC_EVENT_RULE_REGISTRY` in their configuration modules (see {ref}`built-in models <python-built-in-models>`); a new model defines its own (see {ref}`model configurations <python-model-configurations>`).

```python
from phyloom.configs.core import EventRuleCfg
from phyloom.configs.roots import StrCfg
from phyloom.types import Context


@MY_MODEL_EVENT_RULE_REGISTRY.register("my-event-rule")
class MyEventRuleCfg(EventRuleCfg[MyModel]):
    param: StrCfg

    def contextualize(self, context: Context) -> MyEventRule:
        return MyEventRule(self.param.contextualize(context))
```

In configuration data, the rule is selected with its `spec`:

```yaml
model:
  spec: my-model
  events:
    - rule: {spec: my-event-rule, param: "{some_context_variable}"}
      hazard: # ...
```

### ⏱️ Hazards

A hazard gives the per-opportunity instantaneous rate $\lambda(t)$ of an event as a function of the model's simulated clock $t$. Phyloom provides five hazards, each with a configuration counterpart in {py:mod}`phyloom.configs.hazards`:

| Hazard | `spec` | Rate $\lambda(t)$ |
| --- | --- | --- |
| {py:class}`ConstantHazard(rate) <phyloom.simulator.hazards.ConstantHazard>` | `constant` | A fixed positive rate $r$. |
| {py:class}`DeltaHazard() <phyloom.simulator.hazards.DeltaHazard>` | `delta` | None: fires immediately whenever the event has an opportunity. |
| {py:class}`ExponentialHazard(rate, decay) <phyloom.simulator.hazards.ExponentialHazard>` | `exponential` | $r e^{-dt}$: decays for $d > 0$, grows for $d < 0$. |
| {py:class}`SkylineHazard(rates, break_times) <phyloom.simulator.hazards.SkylineHazard>` | `skyline` | Piecewise constant: `rates[i]` applies between consecutive break times. |
| {py:class}`NumericHazard(rate_fn) <phyloom.simulator.hazards.NumericHazard>` | `numeric` | Any non-negative function `rate_fn(t)`, integrated and inverted numerically. |

{py:class}`NumericHazard <phyloom.simulator.hazards.NumericHazard>` covers any rate you can write down as a function, so a custom hazard class is only needed for speed or precision: when the cumulative hazard can be inverted analytically, or when the rate needs a dedicated numerical method.

To implement a new hazard, subclass {py:class}`Hazard <phyloom.simulator.hazards.Hazard>` and implement its single abstract method, {py:meth}`invert(t0, threshold) <phyloom.simulator.hazards.Hazard.invert>`. Given the current time $t_0 \geq 0$ and a threshold $c > 0$, it must return the earliest time at which the cumulative hazard from $t_0$ reaches $c$:

$$
H^{-1}(t_0, c) = \inf\left\{t \geq t_0 : \int_{t_0}^{t} \lambda(s)\,\mathrm{d}s \geq c\right\},
$$

or {py:obj}`None` if the cumulative hazard never reaches $c$ (for example, when the rate decays to zero too quickly or drops to zero permanently). The simulator calls `invert` directly with the current time and a freshly drawn threshold. The built-in hazards reject a negative $t_0$ or a non-positive $c$ with a {py:exc}`ValueError`, and a custom hazard should do the same, so that calling it directly with invalid inputs fails loudly. Keep in mind that:

- the returned time must not be earlier than `t0`; a proposal in the past stops the simulation with a {py:exc}`RuntimeError`;
- `invert` is called for every active event at every step, with fresh thresholds, so it should be cheap and must not change the hazard's own state;
- parameters are best validated in the constructor, so that invalid values fail when the hazard is built rather than mid-simulation.

```python
from phyloom.simulator.hazards import Hazard


class MyHazard(Hazard):
    def __init__(self, param: float):
        if param <= 0:
            raise ValueError(f"param must be positive (got param={param}).")
        self._param = param

    def invert(self, t0: float, threshold: float) -> float | None:
        # Return the earliest t >= t0 whose cumulative
        # hazard from t0 reaches threshold, or None if it is never reached.

        # Private method from Hazard that checks t0 >= 0 and threshold > 0.
        self._validate(t0, threshold)
        ...
```

To make a rule available in configuration data, subclass {py:class}`HazardCfgBase <phyloom.configs.hazards.HazardCfgBase>`, declare its parameters as fields, build the runtime hazard in {meth}`contextualize <phyloom.configs.hazards.HazardCfgBase.contextualize>`, and register the class in {py:data}`HAZARD_REGISTRY <phyloom.configs.hazards.HAZARD_REGISTRY>`. Hazards are shared by all models, so a registered hazard can be used with any event rule:

```python
from phyloom.configs.hazards import HAZARD_REGISTRY, HazardCfgBase
from phyloom.configs.roots import FloatCfg
from phyloom.types import Context


@HAZARD_REGISTRY.register("my-hazard")
class MyHazardCfg(HazardCfgBase):
    param: FloatCfg

    def contextualize(self, context: Context) -> MyHazard:
        return MyHazard(self.param.contextualize(context))
```

In configuration data, the hazard is selected with its `spec`:

```yaml
model:
  # ...
  events:
    - rule: # ...
      hazard: {spec: my-hazard, param: 2 * some_context_variable}
```

## 🧬 Models

A {py:class}`Model <phyloom.simulator.core.Model>` is the base class of every simulator. It owns the simulated clock ({py:attr}`current_time <phyloom.simulator.core.Model.current_time>`), a seedable random generator ({py:attr}`rng <phyloom.simulator.core.Model.rng>`), a list of stochastic events, and a schedule of deterministic actions. Its constructor takes:

- `events`: stochastic {py:class}`Event <phyloom.simulator.core.Event>` objects;
- `schedule`: `(time, action)` pairs, where `action` is a callable that receives and mutates the model when the clock reaches the absolute, non-negative `time`.

Both can be extended while the simulation is running, with {py:meth}`add_event <phyloom.simulator.core.Model.add_event>` and {py:meth}`add_action <phyloom.simulator.core.Model.add_action>` (whose time must not be in the past). Scheduling actions from within actions or rules is how per-entity clocks, delays, and interventions are implemented.

A concrete model subclass adds the domain state and two kinds of methods:

- **primitives**, which change the state (for example, creating, ending, or relabeling entities) and are called by event rules and scheduled actions;
- **queries**, which count, list, or draw entities without changing anything, and are used by event eligibility criteria, rate multipliers, stopping and acceptance criteria, and logs.

```python
from phyloom.simulator.core import Model


class MyModel(Model):
    def __init__(self, param, events=(), schedule=()):
        super().__init__(events, schedule)
        # Initialize the domain state here.

    # Primitives: change the state.
    def do_something(self, *args) -> None: ...

    # Queries: inspect the state without changing it.
    def count_something(self, *args) -> int: ...
```

A model advances with {py:meth}`step <phyloom.simulator.core.Model.step>`, which moves the clock to the earliest proposed event time, scheduled action, or `max_time`, and applies everything due at that time. It returns `False` once nothing more can happen or the next transition lies beyond `max_time`. A simulation is a loop around it; this is exactly what the runner does for every trial:

```python
model.rng.seed(42)  # make the trial reproducible
while model.step(max_time=100.0):
    if stop_criterion(model):  # any condition on the model state
        break
```

### 🕸️ Network models

Models that build phylogenetic trees or networks derive from {py:class}`NetModel <phyloom.simulator.net.NetModel>`, which is the base of the built-in BDSH, coalescent, and epidemic models. It records every lineage as a node and every ancestry relation as an edge, labels each lineage with a string **state**, and keeps track of which lineages are currently **active**. It provides:

- queries over active lineages: {py:meth}`get_current_lineages <phyloom.simulator.net.NetModel.get_current_lineages>`, {py:meth}`count_current_lineages <phyloom.simulator.net.NetModel.count_current_lineages>`, {py:meth}`draw_current_lineages <phyloom.simulator.net.NetModel.draw_current_lineages>` (all optionally restricted to a state), and {py:meth}`state_of <phyloom.simulator.net.NetModel.state_of>`;
- {py:meth}`history <phyloom.simulator.net.NetModel.history>`, which materializes the simulated history as a {py:class}`Net <phyloom.core.Net>` (or a {py:class}`Tree <phyloom.core.Tree>` with `return_as="tree"`), with edge lengths computed from lineage times. Passing a `skeleton` of leaf lineages returns only their ancestry, for example the history of the sampled lineages only.

A subclass defines its timing and primitives:

- {py:meth}`get_root <phyloom.simulator.net.NetModel.get_root>`, {py:attr}`origin <phyloom.simulator.net.NetModel.origin>`, and {py:meth}`time_of <phyloom.simulator.net.NetModel.time_of>`, which locate the history in time. Edge lengths are differences of `time_of` values, and the stem runs from `origin` to the root;
- primitives built on the protected helpers `_get_new_lineage(state)`, which creates an active lineage and returns its id, and `_finalize_lineage(lineage)`, which deactivates one, together with adding `(parent, child)` entries to `self._edges` to record ancestry.

When a built-in model already has most of the primitives you need, subclass it rather than {py:class}`NetModel <phyloom.simulator.net.NetModel>`, and add only what is new.

(python-built-in-models)=

### 🧰 Built-in models

Phyloom ships three network models. Each one comes with runtime event rules built on its primitives, and with a configuration module that registers the model and its rules:

| Model | Simulates | Starts from | Primitives | Additional queries |
| --- | --- | --- | --- | --- |
| {py:class}`BDSHModel <phyloom.simulator.bdsh.BDSHModel>` | Birth, death, sampling, and hybridization, forward in time | One lineage in `init_state` | {py:meth}`birth_from <phyloom.simulator.bdsh.BDSHModel.birth_from>`, {py:meth}`continue_as <phyloom.simulator.bdsh.BDSHModel.continue_as>`, {py:meth}`finalize <phyloom.simulator.bdsh.BDSHModel.finalize>`, {py:meth}`sample <phyloom.simulator.bdsh.BDSHModel.sample>`, {py:meth}`rho_sample <phyloom.simulator.bdsh.BDSHModel.rho_sample>`, {py:meth}`hybridize <phyloom.simulator.bdsh.BDSHModel.hybridize>` | {py:meth}`get_sampled_lineages <phyloom.simulator.bdsh.BDSHModel.get_sampled_lineages>`, {py:meth}`count_sampled_lineages <phyloom.simulator.bdsh.BDSHModel.count_sampled_lineages>` |
| {py:class}`CoalescentModel <phyloom.simulator.coalescent.CoalescentModel>` | Ancestry of a population of lineages, backward in time | `init_population` lineages per state | {py:meth}`spawn <phyloom.simulator.coalescent.CoalescentModel.spawn>`, {py:meth}`retrace <phyloom.simulator.coalescent.CoalescentModel.retrace>`, {py:meth}`coalesce <phyloom.simulator.coalescent.CoalescentModel.coalesce>` | None |
| {py:class}`EpidemicModel <phyloom.simulator.epidemic.EpidemicModel>` | Transmission in a compartmental epidemic, forward in time | One lineage in `init_state` and `init_pools` counts | {py:meth}`infection <phyloom.simulator.epidemic.EpidemicModel.infection>`, {py:meth}`recovery <phyloom.simulator.epidemic.EpidemicModel.recovery>`, {py:meth}`migration <phyloom.simulator.epidemic.EpidemicModel.migration>`, {py:meth}`flow <phyloom.simulator.epidemic.EpidemicModel.flow>` | {py:attr}`pools <phyloom.simulator.epidemic.EpidemicModel.pools>`, {py:meth}`get_sampled_lineages <phyloom.simulator.epidemic.EpidemicModel.get_sampled_lineages>`, {py:meth}`count_sampled_lineages <phyloom.simulator.epidemic.EpidemicModel.count_sampled_lineages>` |

The coalescent model runs backward: its clock measures time into the past, and its history can only be built once all lineages have coalesced into one root. The BDSH and epidemic models run forward and additionally record **sampled lineages**, which are typically passed to {py:meth}`history <phyloom.simulator.net.NetModel.history>` as a skeleton to extract the part of the history ancestral to the observations.

Every built-in rule is a runtime class in the model's simulator package, with a configuration class registered under a `spec` key in the model's event-rule registry:

| Model | Configuration (`spec`) | Event-rule registry | Runtime rules (`spec`) |
| --- | --- | --- | --- |
| BDSH | {py:class}`BDSHModelCfg <phyloom.configs.bdsh.BDSHModelCfg>` (`bdsh`) | {py:data}`BDSH_EVENT_RULE_REGISTRY <phyloom.configs.bdsh.BDSH_EVENT_RULE_REGISTRY>` | {py:class}`Birth <phyloom.simulator.bdsh.Birth>` (`birth`), {py:class}`Death <phyloom.simulator.bdsh.Death>` (`death`), {py:class}`Migration <phyloom.simulator.bdsh.Migration>` (`migration`), {py:class}`Sampling <phyloom.simulator.bdsh.Sampling>` (`sampling`), {py:class}`LDH <phyloom.simulator.bdsh.LDH>` (`ldh`), {py:class}`LNH <phyloom.simulator.bdsh.LNH>` (`lnh`), {py:class}`LGH <phyloom.simulator.bdsh.LGH>` (`lgh`) |
| Coalescent | {py:class}`CoalescentModelCfg <phyloom.configs.coalescent.CoalescentModelCfg>` (`coalescent`) | {py:data}`COALESCENT_EVENT_RULE_REGISTRY <phyloom.configs.coalescent.COALESCENT_EVENT_RULE_REGISTRY>` | {py:class}`Retrace <phyloom.simulator.coalescent.Retrace>` (`retrace`), {py:class}`Coalesce <phyloom.simulator.coalescent.Coalesce>` (`coalesce`) |
| Epidemic | {py:class}`EpidemicModelCfg <phyloom.configs.epidemic.EpidemicModelCfg>` (`epidemic`) | {py:data}`EPIDEMIC_EVENT_RULE_REGISTRY <phyloom.configs.epidemic.EPIDEMIC_EVENT_RULE_REGISTRY>` | {py:class}`Infection <phyloom.simulator.epidemic.Infection>` (`infection`), {py:class}`Recovery <phyloom.simulator.epidemic.Recovery>` (`recovery`), {py:class}`Migration <phyloom.simulator.epidemic.Migration>` (`migration`), {py:class}`Flow <phyloom.simulator.epidemic.Flow>` (`flow`) |

(python-model-configurations)=

### 🧾 Model configurations

A model becomes selectable with `spec` in configuration data through a registered {py:class}`ModelCfgBase <phyloom.configs.core.ModelCfgBase>` subclass. A complete model extension consists of:

1. the runtime model, described above;
2. its event rules and their configurations, described in {ref}`event rules <python-event-rules>`;
3. an **event-rule registry**, a {py:class}`Registry <phyloom.utils.Registry>` of model-specific {py:class}`EventRuleCfg <phyloom.configs.core.EventRuleCfg>` classes, together with an {py:obj}`Annotated <typing.Annotated>` alias that attaches the registry's {py:attr}`validator <phyloom.utils.Registry.validator>`;
4. a model configuration that declares the model's own parameters plus its `events` and `schedule` fields, and builds the runtime model in {py:func}`contextualize <phyloom.configs.core.ModelCfgBase.contextualize>`.

```python
from typing import Annotated, TypeAlias

from phyloom.configs.core import (
    MODEL_REGISTRY,
    EventCfg,
    EventRuleCfg,
    ModelCfgBase,
    ScheduledEventCfg,
)
from phyloom.configs.roots import FloatCfg
from phyloom.types import Context
from phyloom.utils import Registry

MY_MODEL_EVENT_RULE_REGISTRY: Registry[EventRuleCfg[MyModel]] = Registry(
    "My model event rule", EventRuleCfg[MyModel]
)
MyModelEventRuleCfg: TypeAlias = Annotated[
    EventRuleCfg[MyModel], MY_MODEL_EVENT_RULE_REGISTRY.validator
]


@MODEL_REGISTRY.register("my-model")
class MyModelCfg(ModelCfgBase):
    param: FloatCfg
    events: tuple[EventCfg[MyModelEventRuleCfg], ...] = ()
    schedule: tuple[ScheduledEventCfg, ...] = ()

    def contextualize(self, context: Context) -> MyModel:
        return MyModel(
            self.param.contextualize(context),
            events=[event.contextualize(context) for event in self.events],
            schedule=[
                item for entry in self.schedule for item in entry.contextualize(context)
            ],
        )
```

{py:class}`EventCfg <phyloom.configs.core.EventCfg>` handles the `rule`, `hazard`, and `rate_multiplier` fields of each event, and {py:class}`ScheduledEventCfg <phyloom.configs.core.ScheduledEventCfg>` turns each `schedule` entry into one `(time, action)` pair per listed time. The model is then configured like a built-in one:

```yaml
model:
  spec: my-model
  param: 0.5
  events:
    - rule: {spec: my-event-rule, param: "..."}
      hazard: # ...
  schedule:
    - times: [10.0, 20.0]
      action: model.do_something(...)
```

## 🔌 Plugins

A registration decorator such as `@MODEL_REGISTRY.register("my-model")` only runs when Python imports the file that contains it. The `phyloom` command cannot know which of your files to import, so a configuration that uses `spec: my-model` would fail with an unknown `spec`. To fix this, you turn your code into a **plugin**: a small Python package that tells Phyloom which files to import before it reads any configuration.

You don't need to publish anything to do this: the package can stay on your computer. The steps below use [uv](https://docs.astral.sh/uv/getting-started/installation/), a tool that creates Python projects and gives each one its own isolated **environment**, a folder in which Phyloom and your code are installed together.

1. **Create the project.** Choose a name for your plugin and run:

   ```bash
   uv init --package phyloom-myplugin
   cd phyloom-myplugin
   ```

   This creates the following files:

   ```text
   phyloom-myplugin/
   ├── pyproject.toml
   ├── README.md
   └── src/
       └── phyloom_myplugin/
           └── __init__.py
   ```

   `src/phyloom_myplugin/` is the package itself, the folder your code goes in. Its name uses underscores because Python names cannot contain hyphens. `pyproject.toml` describes the package: its name, its version, the other packages it needs, and settings that other tools can read. You won't need the `[project.scripts]` table that uv adds to `pyproject.toml`, or the `main` function in `__init__.py`, so you can delete both.

2. **Add Phyloom as a dependency.**

   ```bash
   uv add phyloom
   ```

   This adds Phyloom to the `dependencies` list in `pyproject.toml` and installs it, together with your own package, into the project environment (the `.venv/` folder).

3. **Write your extensions.** Put your classes and their registration decorators, as described in the previous sections, in a Python file inside the package, for example `src/phyloom_myplugin/my_module.py`.

4. **Tell Phyloom what to import.** Add these lines at the end of `pyproject.toml`:

   ```toml
   [project.entry-points."phyloom.plugins"]
   my-plugin = "phyloom_myplugin.my_module"
   ```

   This declares an **entry point**: a note stored with the installed package that other programs can look up. Before reading a configuration, the `phyloom` command collects every `phyloom.plugins` entry point from the installed packages and imports the module each one names. That import runs your decorators. The name on the left can be anything. The value on the right is the module's import path: the package folder name, a dot, and the file name without `.py`. If your code is spread over several files, add one line for each file that registers something. Phyloom registers its own built-in models this way.

5. **Run your configurations.** Write a YAML configuration that selects your extensions by their `spec` keys, as described in the [YAML user guide](yaml), and save it in the project folder, for example as `config.yaml`. Then, from the project folder:

   ```bash
   uv run phyloom config.yaml
   ```

   `uv run` runs the command inside the project environment, where your plugin is installed, and changes to your Python files take effect right away.

Each `spec` key can be registered only once per registry, and registering a second class under an existing key raises an error. Give your extensions distinctive names so that they don't clash with the built-in ones or with other plugins.

The [plugins](../plugins) are complete, thoroughly commented, and ready-to-use project examples.

## 🏃 Running simulations from Python

To run YAML configurations from a Python script or notebook, call {py:func}`phyloom.run <phyloom.run>` with the path to a configuration file, or to a directory whose `.yaml` files should all be run. It does exactly what the `phyloom` command does: it loads the installed plugins, validates each configuration, and generates its dataset.

```python
from phyloom import run

run("config.yaml")
```

When a simulation does not fit the runner's workflow, write the per-sample logic yourself and use {py:func}`run_simulations <phyloom.simulator.utils.run_simulations>` to execute it in parallel. It calls a function with each sample id and an independent seed derived from a master seed, and collects the metadata dictionaries it returns into a {py:class}`pandas.DataFrame`:

```python
from phyloom.simulator.utils import run_simulations


def simulate(sample_id: int, seed: int) -> dict[str, object]:
    model = ...  # build a fresh model for this sample
    model.rng.seed(seed)
    while model.step(max_time=100.0):
        ...
    ...  # write outputs, e.g. model.history().dump(...) for network models
    return {"final_time": model.current_time}


metadata = run_simulations(100, simulate, seed=42, n_jobs=4)
```

Every [example](../examples) includes a complete script of this kind next to its YAML configuration.