# 🧭 Fundamentals

Phylogenetic simulation generates evolutionary histories from explicit mathematical models of lineage dynamics through time. By generating datasets where the true underlying history is known by construction, simulations provide a crucial benchmark for evaluating inference methods, testing hypothesis-driven models, and understanding complex biological processes.

## 🔀 Generative processes and histories

Simulation models represent biological processes through discrete **events**—such as lineage speciation, extinction, migration, observation, hybridization, or coalescence. Each event applies to one or more lineages, altering their properties, terminating them, or giving rise to new lineages. 

To track biological variation across lineages, each lineage is associated with a **state label**. These labels represent discrete or continuous attributes bound directly to a lineage, such as its geographic location, phenotypic trait, host compartment, or infection status. Events can trigger state transitions, updating these attributes as the simulation progresses.

At any given point in a simulation run, **active lineages** are those ongoing, unterminated lineages that remain eligible to undergo state transitions or participate in subsequent events. Together, these active lineages, their associated metadata, and global parameters define the complete **system state** at that time.

A single simulation run produces a **full history**: the complete record of every lineage and event generated over time. Mathematically, this history is structured as a **directed acyclic graph (DAG)** where edges run from ancestors to descendants, and take the form of either a **tree** or a **network**.

When lineages strictly split and diverge, the resulting structure is a phylogenetic tree, where every node except the root has a single parent. Internal nodes mark branching events, leaves represent sampled individuals or taxa, and edge lengths quantify elapsed time or evolutionary distance. When lineages merge or exchange genetic material—capturing reticulate dynamics like hybridization, lateral gene transfer, or recombination—a descendant node can have multiple parents, yielding a phylogenetic network.

How these graphs map to biological reality depends entirely on the domain: in macroevolution, nodes represent speciation, extinction, or hybridization across species; in epidemiology, lineages trace host-to-host transmission chains during an epidemic; and in population genetics, branches trace the shared ancestry and gene flow of individuals or populations.

When a model includes a sampling or observation process, the full history serves as a latent history that can be pruned to produce an **observed phylogeny**. This observed phylogeny retains the sampled tips and their shared ancestry, while discarding unobserved lineages that leave no sampled descendants.

```{figure} ../figures/fundamentals/history.svg
:width: 90%
:align: center

The full history includes sampled lineages, unobserved terminations, and reticulation; pruning it retains the ancestry of the observed tips, including any hybridization ancestral to them.
```

## 🧩 Event rules and primitives

Phyloom decouples a simulation's discrete state transitions from their temporal execution. Simulations are driven by an **event scheduler** that strictly separates an event's structural eligibility and state transformation from its timing:

* **Eligibility and effect** are defined by an event rule that specifies how to compute its number of *opportunities*—the total number of distinct ways an event can act upon the current system state—and how applying one chosen opportunity mutates the state (e.g., creating, terminating, or modifying lineages);
* **Timing** is governed independently by either an explicit **scheduling time** (for deterministic or scheduled events) or a **rate function** (for stochastic hazard-driven events).

Event rules are model-specific and are built by composing a small set of **lineage-level primitives** exposed by a given model. Phyloom provides three built-in model families:

* **Birth-death-sampling-hybridization (BDSH)** models for forward-in-time branching processes with unbounded population growth, lineage sampling, and reticulation.
* **Coalescent models** for tracing population ancestry backward in time.
* **Compartment-based epidemic models** for simulating the spread of infectious diseases across structured populations (such as SIR, SEIR, and SEIRS).

In this section, we describe the lineage-level primitives for these three built-in models. In the next section, we describe how the scheduler uses event rules and rate functions to propose event times.

### 🌱 Birth-death-sampling-hybridization models

The birth-death-sampling-hybridization (BDSH) model simulates evolutionary histories forward in time. Lineage dynamics in BDSH are built from five core primitives:

* **`Finalize` (termination)** ends an active lineage without recording an observation, representing unobserved extinction, natural mortality, or clearance.
* **`Sample` (observation)** records a lineage as an observed tip. Under **sampling with removal** (e.g., isolating an infected host upon testing), the lineage terminates. Under **sampling without removal** (e.g., fossil collection), the lineage continues as an active lineage alongside the newly recorded tip.
* **`Continue as` (state transition)** replaces an active lineage with a continuing descendant while updating its state label, modeling processes like geographical migration or phenotypic change.
* **`Birth from` (divergence)** replaces an active lineage with two active descendants, modeling cladogenesis, speciation, or transmission. Each descendant can independently inherit or switch the parent's state label.
* **`Hybridize` (convergence)** merges two active parent lineages into a single active hybrid descendant, modeling reticulate events such as gene flow.

```{figure} ../figures/fundamentals/bdsh-primitives.svg
:width: 90%
:align: center

Forward-time BDSH primitives show how events end or observe lineages, change lineage state, create two descendants, or merge two parents into a hybrid descendant.
```

#### Example: composing hybridization events in Phyloom

To illustrate how Phyloom composes lineage primitives into higher-level event rules, consider how hybridization affects net lineage count. Depending on whether parental lineages persist after a reticulation event, BDSH exposes three distinct hybridization event rules:

* **LDH (lineage-degenerative hybridization)** applies **`hybridize`** directly to two active parents. The parent lineages terminate, leaving a single active hybrid descendant (net change: -1 active lineage).
* **LNH (lineage-neutral hybridization)** duplicates one parent via **`birth from`** prior to hybridization. The non-duplicated parent terminates, leaving the continuing parental lineage and the new hybrid active (net change: 0 active lineages).
* **LGH (lineage-generative hybridization)** duplicates both parents via **`birth from`** prior to hybridization. Both parental lineages continue alongside the new hybrid descendant (net change: +1 active lineage).

```{figure} ../figures/fundamentals/bdsh-hybridizations.svg
:width: 90%
:align: center

The three forward-time hybridization rules differ in which parents continue: LDH retains neither, LNH one, and LGH both, producing net changes of −1, 0, and +1 active lineages, respectively.
```

### 🔗 Coalescent models

Coalescent models trace the gene genealogy of a set of sampled lineages **backward in time** toward their most recent common ancestor (MRCA). Unlike forward-in-time branching models where population size expands or fluctuates dynamically, standard coalescent models fix or specify population size trajectories over time, modeling shared ancestry as a stochastic merging process.

Backward-in-time ancestral dynamics are governed by three core primitives:

* **`Coalescence` (ancestral merging)** replaces a pair of active lineages with a single ancestral parent lineage, representing the merging of two lineages into a common ancestor backward in time.
* **`Spawn` (sample introduction)** introduces a new active lineage at a specified scheduled backward-in-time point, representing an additional sample taken at a given historical time point (e.g., heterochronous sampling or serial sample collection).
* **`Retrace` (ancestral transition)** replaces a single active lineage with an ancestral parent lineage while updating its state label, representing ancestral state transitions backward in time (e.g., tracing a lineage migrating from one geographic location to another).

```{figure} ../figures/fundamentals/coalescent-primitives.svg
:width: 100%
:align: center

Backward-time coalescent primitives show how events merge lineages into an ancestor, introduce a lineage at a scheduled sample time, or change ancestral state as lineages are traced from the present toward older ancestors.
```

### 🦠 Compartmental epidemic models

Compartmental epidemic models integrate lineage dynamics with classical host population pools (such as SIR, SEIR, SEIRS, etc.). Host individuals move between discrete state compartments, while transmission events create explicit host-to-host transmission lineages forward in time. 

In this framework, the total host population is partitioned across named **compartments**. Active lineages represent currently infectious hosts, while non-infectious compartments (e.g., susceptible or recovered pools) are tracked as aggregate population counts. 

Lineage and pool dynamics are governed by four core primitives:

* **`Infection` (transmission)** consumes one susceptible individual from a host pool and pairs it with an active infectious lineage to produce two active descendants—one continuing the original transmitter lineage and one representing the newly infected host.
* **`Recovery` (termination or sampling)** ends an active infectious lineage (representing host recovery or isolation upon testing) and increments the target compartment count (e.g., moving the host to a recovered or removed pool). Recovery can optionally trigger the recording of the lineage as a sampled tip, representing the observation of an infected host.
* **`Migration` (state transition)** updates an active lineage's state label (e.g., moving an infectious host between geographic locations or risk groups) without altering net active lineage count.
* **`Pool flow` (compartment transition)** moves individuals between non-lineage population pools (e.g., waning immunity from a recovered pool back to a susceptible pool, or uninfected host migration) without modifying phylogenetic ancestry.

```{figure} ../figures/fundamentals/epidemic-primitives.svg
:width: 100%
:align: center

Forward-time epidemic primitives show how events create transmission descendants, end infectious lineages while moving hosts into destination pools, change lineage state, or move hosts between non-lineage pools.
```

## ⏱️ Event timing and simulation scheduler

Phyloom uses a hybrid event-driven simulation engine that integrates continuous-time stochastic hazard processes, deterministic scheduled interventions, and user-defined stopping criteria.

At any continuous time $t$, the system state $X(t)$ encompasses all active lineages, their assigned state labels, non-lineage population pools, and global system parameters. Between discrete transitions, $X(t)$ remains constant. When a transition occurs, the state updates instantaneously, and the scheduler re-evaluates event eligibility and proposes new stochastic firing times from the updated state $X(t^+)$.

### 🎲 Stochastic events and hazard functions

A stochastic event pairs a domain-specific **event rule** with a time-varying **instantaneous rate** $\lambda(t)$, also called a **hazard function**.

The event rule evaluates the system state $X(t)$ to count the number of **eligible opportunities**, $c$—that is, the total number of individual lineages or valid entity combinations currently capable of undergoing the transition.

Let $n_S$ denote the number of active lineages carrying state label $S$, $n_{\text{total}}$ the total count of active lineages, and $N_{P}$ the population count in an epidemiological compartment $P$. The opportunity count $c$ is determined by the event's structural requirements:

* **Single-lineage events** (e.g., birth, death, migration): $c$ is the total count of active lineages matching the event's target criteria ($c = n_S$ if filtered by an optional state label $S$, or $c = n_{\text{total}}$ if the event applies to all active lineages).
* **Pairwise lineage events** (e.g., hybridization, coalescent merging):
  * *Between distinct states $S_1$ and $S_2$:* $c = n_{S_1} \times n_{S_2}$.
  * *Within the same state $S$:* $c = \binom{n_S}{2} = \frac{n_S(n_S - 1)}{2}$.
* **Lineage–pool events** (e.g., compartmental infection): $c$ is the product of active transmitter lineages in infectious state $I_k$ and susceptible individual host counts in pool $P$ ($c = n_{I_k} \times N_{P}$).

The instantaneous rate $\lambda(t) \ge 0$ represents event occurrence pressure over time. Starting from time $t_0$, the cumulative hazard $H(t_0, t)$ accumulated up to time $t$ is:

$$H(t_0, t) = \int_{t_0}^{t} \lambda(s)\,\mathrm{d}s.$$

To determine when an event fires, the scheduler accounts for the number of opportunities $c$ and an optional state-dependent rate multiplier $m(X(t_0))$ (defaulting to $m = 1$). It draws a random threshold $E \sim \operatorname{Exponential}(1)$ and solves for the target firing time $t_{\mathrm{event}}$:

$$c \cdot m(X(t_0)) \cdot H(t_0, t_{\mathrm{event}}) = E.$$

Inverting the cumulative hazard yields the proposed firing time:

$$t_{\mathrm{event}} = H^{-1}\left(t_0, \frac{E}{c \cdot m(X(t_0))}\right).$$

If $c = 0$, $m = 0$, or $H(t_0, t)$ fails to reach the sampled threshold $E$, no firing time is proposed for that channel.

Under constant rates $\lambda$, this reduces to standard exponential waiting times with total rate $\Lambda = c \cdot m \cdot \lambda$, which is equivalent to the Gillespie Next Reaction / Direct Method algorithms. By leveraging hazard inversion, Phyloom generalizes this race to non-homogeneous Poisson processes (NHPP) where hazards change over time.

Built-in hazards include **constant**, **exponentially changing**, **piecewise constant (`skyline`)**, **immediate (`delta`)**, and **numerically integrated** hazards.

### 🗓️ Scheduled actions and time execution

**Scheduled actions** represent deterministic operations anchored to specific absolute simulation times ($t_{\text{action}}$). They execute interventions such as scheduled sampling, parameter shifts, host introductions, or external state updates. The scheduler does not draw stochastic waiting times for actions.

### 🔁 The Scheduler Loop

At each step, the scheduler evaluates the next transition time across three sources:
1. The earliest proposed time among all active stochastic channels ($t_{\text{stochastic}}$).
2. The earliest upcoming scheduled action ($t_{\text{action}}$).
3. The configured simulation time limit (`max_time`).

The clock advances directly to $t_{\text{next}} = \min(t_{\text{stochastic}}, t_{\text{action}}, \text{max_time})$. If multiple stochastic events or scheduled actions coincide at $t_{\text{next}}$, the scheduler breaks ties by randomly shuffling their execution order before applying their state transitions. The `max_time` boundary is inclusive, ensuring that any events or actions scheduled precisely at $t = \text{max_time}$ are fully applied before the run concludes. A simulation run terminates when the clock reaches `max_time`, a user-defined stopping criterion (such as reaching a target sample count) is satisfied, or the system exhausts all future transitions—occurring when no active stochastic channels have eligible opportunities ($c = 0$) and no remaining scheduled actions exist.

```{figure} ../figures/fundamentals/scheduler-loop.svg
:width: 100%
:align: center

At each step, the scheduler advances to the earliest proposed stochastic event, scheduled action, or time limit. It applies events and actions at that time (shuffling their order when they coincide), updates the system state, and recalculates stochastic proposals until a stopping condition is met or no future transition remains.
```
