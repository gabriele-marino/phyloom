# ⚙️ YAML user guide

Phyloom parses structured YAML configuration files to simulate complex evolutionary and epidemiological dynamics. To set up a simulation, you specify key parameters—including model specifics and execution settings—in a human-readable YAML text file, which Phyloom executes using the following command:

```bash
phyloom path/to/config.yaml
```

This guide details how to define and run a Phyloom simulation using a YAML configuration file. For building and executing models programmatically in Python, refer to the [Python user guide](python). Complete, runnable configuration walkthroughs are available in the [examples](../examples) section.

## 📑 YAML syntax

A Phyloom configuration file relies on nested structures to establish relationships between simulation settings. YAML enforces this hierarchy through its indentation-based syntax, allowing you to define complex, human-readable data structures such as key-value pairings (mappings), ordered lists (sequences), and primitive data values (strings, numbers, booleans).

```yaml
context:                         # Mapping: named context variables
  rate:                          # Key within the context mapping
    type: uniform                # Nested mapping specifying a uniform distribution for the `rate` variable
    low: 0.1
    high: 0.3

model:
  spec: bdsh
  init_state: A
  events:                        # A sequence of event configurations
    - rule: {spec: birth}        # First sequence item; inline mapping using { }
      hazard: {spec: constant, rate: rate}
    - rule: {spec: sampling, removal: false} # Second sequence item
      hazard: {spec: skyline, rates: [0.1, 0.2], break_times: [5.0]} # Square brackets [ ] define an inline list
  schedule:
    - times: [10.0]
      action: | # A vertical bar | keeps the following indented lines together as one multi-line text value
        model.rho_sample(0.5, "A", removal=True)
        model.rho_sample(0.5, "B", removal=False)
```

## 🗂️ Dataset generation settings

Dataset generation settings govern run-level options such as output locations, parallel processing, and reproducibility seeds.

```yaml
output_dir: "phyloom-outputs"   # Target directory for all generated simulation artifacts

# Option 1: Scalar value (generates a single flat dataset)
# n_samples: 100

# Option 2: Split mapping (generates separate train/val/test directories)
n_samples:
  train: 800
  val: 100
  test: 100

n_jobs: 4                      # Number of parallel worker processes
seed: 42                       # Master random seed for reproducibility
```

The output directory layout depends on whether `n_samples` is defined as a scalar value or as a dataset split mapping.

When `n_samples` is set to a single integer (e.g., `n_samples: 100`), Phyloom writes all generated samples directly into a root `data/` folder alongside a single `metadata.csv` file:

```text
phyloom-outputs/
├── metadata.csv
└── data/
    ├── 1/
    │   ├── sampled.nwk
    │   └── history.nwk
    ├── 2/
    └── ...
```

- `metadata.csv`: A summary table containing one row per sample, logging the sample ID alongside its full materialized context values and optional log entries (see below).
- `data/`: Subdirectories indexed by sample ID, starting at 1 (`1/`, `2/`, etc.), containing sample-specific simulation artifacts.

When `n_samples` is defined as a mapping (e.g., `n_samples: {train: 800, val: 100, test: 100}`), Phyloom creates separate subdirectories for each split, each containing its own `metadata.csv` and `data/` folder:

```text
output_dir/
├── train/
│   ├── metadata.csv
│   └── data/
│       ├── 1/
│       │   ├── sampled.nwk
│       │   └── history.nwk
│       └── ...
├── val/
│   ├── metadata.csv
│   └── data/
│       └── ...
└── test/
    ├── metadata.csv
    └── data/
        └── ...
```

## 🎛️ Context

Sample-specific parameters are defined in the top-level `context` mapping. Each key in this mapping is a **context variable** that can be a fixed scalar, a random draw from a prior distribution, or an expression derived from earlier context entries. Phyloom supports all NumPy random-generator distributions, including uniform, lognormal, and integer draws. For a full list of supported distributions and their arguments, see the [NumPy documentation](https://numpy.org/doc/stable/reference/random/generator.html). The evaluated values for these variables form the **materialized context**, which Phyloom uses to configure the model and execution settings for each sample. Materialized context values are also recorded in the sample's `metadata.csv` row.

```yaml
context:
  # Fixed scalar
  generation_time: 2.5
  
  # Derived scalar expression
  birth_rate: 1 / generation_time
  
  # NumPy array manipulation
  base_rates: np.array([0.1, 0.2])
  scaled_rates: base_rates * birth_rate
  min_rate: np.min(scaled_rates)
  
  # Random integer draw from [low, high)
  initial_size:
    type: integers
    low: 20
    high: 50
    
  # Distribution draw with dynamic parameters
  mean_rate: 0.1
  rate:
    type: lognormal
    mean: mean_rate
    sigma: 0.2

  # Choice distribution with dynamic probabilities
  super_spreader_fraction:
    type: uniform
    low: 0.1
    high: 0.3
  initial_state:
    type: choice
    a: "['I_N', 'I_S']"
    p: "[1 - super_spreader_fraction, super_spreader_fraction]"

  # Derived rate calculations based on other context values
  removal_rate: {type: uniform, low: 0.25, high: 0.6}
  sampling_probability: {type: uniform, low: 0.05, high: 0.2}
  sampling_rate: removal_rate * sampling_probability
  unsampled_exit_rate: removal_rate - sampling_rate
```

## 🧬 Model configurations

A model configuration defines initial conditions alongside event-driven, dynamic behaviors. Phyloom supports three model families:

- **{py:class}`BDSH <phyloom.simulator.bdsh.BDSHModel>`** models forward-time lineage evolution with birth, death, sampling, and hybridization dynamics.
- **{py:class}`Coalescent <phyloom.simulator.coalescent.CoalescentModel>`** models backward-time lineage ancestry.
- **{py:class}`Epidemic <phyloom.simulator.epidemic.EpidemicModel>`** models compartment-based epidemic dynamics.

Each family includes its own initial-condition fields, while sharing support for two core sequence blocks:

- **{py:class}`events <phyloom.configs.core.EventCfg>`**: Defines stochastic events, each pairing one of the model's rules, listed below for each family, with a hazard (see {ref}`stochastic events <yaml-stochastic-events>`).
- **{py:class}`schedule <phyloom.configs.core.ScheduledEventCfg>`**: Defines deterministic actions to run at specific simulation times. These are composed of a `times` list and an `action` block. The `times` list specifies one or more simulation timestamps for execution, while the action block consists of executable Python statements run directly against the current `model`, allowing for dynamic lineage manipulations, state changes, and other model-specific operations.

### 🌱 BDSH

The **{py:class}`BDSH <phyloom.configs.bdsh.BDSHModelCfg>`** model requires `init_state` to set the starting lineage state and supports the following stochastic event rules:

* **{py:class}`birth <phyloom.configs.bdsh.BirthCfg>`**: Replaces one eligible lineage with two descendants. An optional `parent_state` filters the parent lineage, while `child_states: [state1, state2]` defines the resulting descendant states. Omitted or `null` child entries inherit the parent state.
* **{py:class}`death <phyloom.configs.bdsh.DeathCfg>`**: Terminates a lineage without sampling. An optional `state` filters eligible lineages.
* **{py:class}`migration <phyloom.configs.bdsh.MigrationCfg>`**: Transitions an active lineage to a new state. Requires `source_state` and `target_state` to specify the origin and destination states.
* **{py:class}`sampling <phyloom.configs.bdsh.SamplingCfg>`**: Records a lineage observation. When the required `removal` flag is `true`, the lineage terminates upon sampling; when `false`, the lineage branches—one descendant is sampled while the other remains active. An optional `state` filters eligible lineages.
* **{py:class}`ldh <phyloom.configs.bdsh.LDHCfg>`**: Merges two parent lineages into a single hybrid lineage (lineage-degenerative hybridization). Optional `parent_states: [state1, state2]` filters parent lineages, and `hybrid_state` specifies the hybrid state. If `hybrid_state` is omitted, both parents must share the same state, which the hybrid inherits.
* **{py:class}`lnh <phyloom.configs.bdsh.LNHCfg>`**: Generates a hybrid descendant from two lineages where one parent continues and the second terminates (lineage-neutral hybridization). Optional `continuing_parent_state` and `terminating_parent_state` filter the parent lineages (must be provided together). An optional `new_parent_state` updates the continuing parent's state (defaults to its existing state if omitted). The optional `hybrid_state` sets the hybrid state; if omitted, both parents must share the same state.
* **{py:class}`lgh <phyloom.configs.bdsh.LGHCfg>`**: Produces a hybrid descendant while allowing both parent lineages to continue (lineage-generative hybridization). Optional `parent_states: [state1, state2]` filters the parents, while `new_parent_states: [state1, state2]` assigns updated states to the continuing parents. Omitted or `null` entries inherit their respective parent states. An optional `hybrid_state` assigns the hybrid state; if omitted, both parents must share the same state.

```yaml
context:
  schedule_time:
    type: uniform
    low: 5.0
    high: 15.0
  sample_probability:
    type: uniform
    low: 0.1
    high: 0.5
  init_state:
    type: choice
    a: "['A', 'B']"
    p: "[0.5, 0.5]"

model:
  spec: bdsh
  init_state: "{init_state}" # Placeholder interpolation for context-dependent string value
  events:
    - rule: {spec: birth, parent_state: A, child_states: [A, B]}
      hazard: # ...
    - rule: {spec: death, state: B}
      hazard: # ...
    - rule: {spec: migration, source_state: B, target_state: A}
      hazard: # ...
    - rule: {spec: sampling, state: A, removal: true}
      hazard: # ...
    - rule: {spec: ldh, parent_states: [A, A], hybrid_state: H}
      hazard: # ...
    - rule:
        spec: lnh
        continuing_parent_state: A
        terminating_parent_state: A
        new_parent_state: A
        hybrid_state: H
      hazard: # ...
    - rule:
        spec: lgh
        parent_states: [A, A]
        hybrid_state: H
        new_parent_states: [A, A]
      hazard: # ...
  schedule:
    # Sample lineages in state "A" with probability sample_probability at schedule_time
    - times: [schedule_time] 
      action: model.rho_sample(sample_probability, "A", removal=True)
```

### 🔗 Coalescent

The **{py:class}`Coalescent <phyloom.configs.coalescent.CoalescentModelCfg>`** model requires `init_population`, a mapping from state names to positive initial lineage counts, and supports the following stochastic event rules:

* **{py:class}`retrace <phyloom.configs.coalescent.RetraceCfg>`**: Replaces a current lineage with an ancestor in the required `ancestral_state`. An optional `current_state` filters eligible lineages.
* **{py:class}`coalesce <phyloom.configs.coalescent.CoalesceCfg>`**: Merges two lineages into a single common ancestor. An optional `current_states: [state1, state2]` list filters eligible pairs. The optional `ancestral_state` sets the resulting ancestor's state; if omitted, both lineages must share the same state, which the ancestor inherits.

```yaml
context:
  schedule_times:
    type: uniform
    low: 5.0
    high: 15.0
    size: 50

model:
  spec: coalescent
  init_population: {A: 1, B: 2}
  events:
    - rule: {spec: retrace, current_state: A, ancestral_state: B}
      hazard: # ...
    - rule: {spec: coalesce, current_states: [B, B], ancestral_state: A}
      hazard: # ...
  schedule:
    # Add a new lineage in state "B" at each time in schedule_times
    - times: np.sort(schedule_times)
      action: model.spawn("B")
```

### 🦠 Epidemic

The **{py:class}`Epidemic <phyloom.configs.epidemic.EpidemicModelCfg>`** model requires two primary initializations: `init_state` defines the state of the initial infectious lineage, while `init_pools` maps pool names to their non-negative initial population counts. Pools omitted from `init_pools` start at zero. The model supports the following stochastic event rules:

* **{py:class}`infection <phyloom.configs.epidemic.InfectionCfg>`**: Consumes one member from the required `recipient_pool` and produces two descendants from an eligible source lineage. An optional `source_state` filters source lineages, while `child_states: [state1, state2]` assigns descendant states (`null` entries inherit the source state).
* **{py:class}`recovery <phyloom.configs.epidemic.RecoveryCfg>`**: Terminates an eligible lineage and adds one member to the required `destination_pool`. An optional `source_state` filters lineages, and `sample` controls whether the lineage is recorded as an observation 
* **{py:class}`migration <phyloom.configs.epidemic.MigrationCfg>`**: Transitions an active lineage to a new state. Requires `source_state` and `target_state` to specify the origin and destination states.
* **{py:class}`flow <phyloom.configs.epidemic.FlowCfg>`**: Transfers one member from the required `source_pool` to the required `destination_pool` without altering lineages.

```yaml
context:
  schedule_time:
    type: uniform
    low: 5.0
    high: 15.0
  init_S:
    type: integers
    low: 100
    high: 200
  flow_probability:
    type: uniform
    low: 0.1
    high: 0.5

model:
  spec: epidemic
  init_state: I
  init_pools: {S: init_S}
  events:
    - rule:
        spec: infection
        recipient_pool: S
        source_state: I
        child_states: [I, E]
      hazard: # ...
    - rule: {spec: recovery, source_state: I, destination_pool: R, sample: true}
      hazard: # ...
    - rule: {spec: migration, source_state: E, target_state: I}
      hazard: # ...
    - rule: {spec: flow, source_pool: S, destination_pool: R}
      hazard: # ...
  schedule:
    # Move a fraction of the S pool to R at the scheduled time
    - times: [schedule_time]
      action: |
        for _ in range(int(flow_probability * model.pools["S"])):
          model.flow("S", "R")
```

(yaml-stochastic-events)=

## 🎲 Configuring stochastic events

A stochastic {py:class}`event <phyloom.configs.core.EventCfg>` configuration specifies *which* transition can occur and *when* it is eligible to fire. Each event pairs a `rule` of its model, from those listed above, with a per-opportunity, time-dependent instantaneous rate function ({py:class}`hazard <phyloom.configs.hazards.HazardCfgBase>`). The firing rate of an event can also be scaled dynamically by an optional model state-dependent `rate_multiplier`.

Phyloom supports five built-in hazard shapes:

- **{py:class}`constant <phyloom.configs.hazards.ConstantHazardCfg>`**: Fires at a fixed positive `rate` over time.
- **{py:class}`delta <phyloom.configs.hazards.DeltaHazardCfg>`**: Fires immediately upon becoming eligible; requires no additional parameters.
- **{py:class}`exponential <phyloom.configs.hazards.ExponentialHazardCfg>`**: Defined by a positive `rate` at time $t=0$ and an exponential `decay` parameter. Positive `decay` makes the rate fall, negative `decay` makes it grow with simulation time, and zero keeps it constant.
- **{py:class}`skyline <phyloom.configs.hazards.SkylineHazardCfg>` (piecewise-constant):** Defined by non-negative `rates` and strictly increasing, positive `break_times`. Must provide exactly one more rate than the number of break times; each break time marks the start of the next rate interval.
- **{py:class}`numeric <phyloom.configs.hazards.NumericHazardCfg>`**: Uses a custom-defined expression `rate_fn` to compute a non-negative rate as a function of simulation time `t`.

To dynamically scale hazard rates based on the model state, specify the optional `rate_multiplier` field. Defined as an expression of `model`, it provides direct access to real-time simulation properties and methods, such as the current clock time or active lineage counts. The expression must evaluate to a non-negative scalar that directly scales the hazard rate, where a value of $0$ temporarily disables the event.

```yaml
context:
  event_rate: 0.1
  decay: 0.05
  change_time:
    type: uniform
    low: 0.1
    high: 10.0
  rate_before: 0.1
  rate_after: 0.2
  base_rate: 0.1
  skyline_rates:
    type: uniform
    low: 0.1
    high: 0.5
    size: 10
  break_times:
    type: uniform
    low: 0.1
    high: 10.0
    size: 9

model:
  # ...
  events:
    - rule: # ...
      hazard: {spec: constant, rate: event_rate}
      rate_multiplier: 1 / model.count_current_lineages("A") # Inversely scales rate by the count of lineages in state "A"
    - rule: # ...
      hazard: {spec: delta}
    - rule: # ...
      hazard: {spec: exponential, rate: event_rate, decay: decay}
      rate_multiplier: float(model.current_time < 2.0) # Disables the event after time 2.0
    - rule: # ...
      hazard:
        spec: skyline
        rates: [rate_before, rate_after, 0.3]
        break_times: [change_time, 15.0]
    - rule: # ...
      hazard:
        spec: skyline
        rates: skyline_rates
        break_times: break_times
    - rule: # ...
      hazard:
        spec: numeric
        rate_fn: base_rate * np.exp(-decay * t)
```

## 🏃 Execution settings

Execution settings control when a trial ends, whether it is accepted, and what is recorded in the output.

- **`max_time`** optionally sets a positive upper bound on simulated time. Stochastic events and scheduled actions due exactly at this bound are applied before the trial ends.
- **`stop_criterion`** is an optional Python expression evaluated against the current `model` after each simulation step; returning `True` ends the trial.
- **`acceptance_criterion`** is an optional Python expression evaluated against the `model` when a trial ends; returning `False` rejects the trial and retries with the same materialized context.
- **`stop_hook`** is an optional block of Python statements run on the accepted `model` after the trial ends and before logs and output hooks are evaluated.
- **`max_rejections`** limits rejected trials for one context. Once the count exceeds it, that context is written to `max_rejections_exceeded_contexts.csv` in the run's output directory (`output_dir` for an unsplit run or `output_dir/<split>` for a split run), then replaced with a newly sampled context.
- **`timeout`** is an optional wall-clock limit in seconds for one trial. Timed-out contexts are written to `timed_out_contexts.csv` in the run's output directory (`output_dir` for an unsplit run or `output_dir/<split>` for a split run), then replaced with newly sampled contexts.
- **`logs`** maps metadata column names to Python expressions evaluated on the accepted `model`, after `stop_hook` runs. Their results are written to `metadata.csv`.
- **`output_hooks`** is a required list of Python statement blocks run for each accepted sample, after logs are evaluated. Each block receives the accepted `model` and `output_dir`, which is the sample-specific output directory where it can write files.
- **`post_commands`** is an optional list of shell commands run last for each accepted sample, after the output hooks, with `{name}` placeholders filled from the materialized context and the sample-specific `output_dir`.

```yaml
context:
  target_samples: {type: integers, low: 10, high: 21}
  birth_rate: 0.4
  sampling_rate: 0.2
  clock_rate: {type: uniform, low: 0.001, high: 0.01}
  seq_length: {type: integers, low: 500, high: 1001}

model:
  spec: bdsh
  # ...

# Stop when the number of sampled lineages reaches the target sample size
stop_criterion: model.count_sampled_lineages() >= target_samples

# Accept only trials that finish with at least one active lineage (i.e., the model is not extinct)
acceptance_criterion: model.count_current_lineages() > 0

# On accepted trials, sample each active I lineage with probability 0.5
# and remove sampled lineages
stop_hook: model.rho_sample(0.5, "I", removal=True)

max_time: 100.0 # Execution stops if the simulated clock reaches 100.0 time units

max_rejections: 100 # Abandon a context after the rejection count exceeds 100

timeout: 60 # Abandon a trial if it runs longer than 60 seconds of wall-clock time

# Store the accepted model's sampled-lineage count as metadata
logs:
  sampled_lineages: model.count_sampled_lineages()

# Write the full lineage history and the sampled lineage history to
# newick files in the sample-specific output directory
output_hooks:
  - model.history().dump(output_dir / "history.nwk")
  - model.history(model.get_sampled_lineages()).dump(output_dir / "sampled.nwk")

# Run AliSim on the sampled tree to simulate a DNA alignment along it
# (requires IQ-TREE 3 installed with its `iqtree3` command on your PATH)
post_commands:
  - iqtree3 --alisim {output_dir}/alignment -t {output_dir}/sampled.nwk
    -m JC --length {seq_length} --branch-scale {clock_rate}
    -af fasta
```
