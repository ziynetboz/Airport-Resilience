# Airport Resilience ABM: Theoretical Basis, Assumptions, and Implementation

This document provides a comprehensive explanation of the Airport Resilience Agent-Based Model (ABM), including its theoretical foundations, modeling assumptions, and implementation details.

---

## 1. Theoretical Basis

### 1.1 Resilience Framework

The model is grounded in **operational resilience** theory: the ability of a system to absorb disturbances, maintain function during disruption, and recover afterward. For airports, resilience is measured by:

- **Absorption**: How much throughput drops when a shock occurs (capacity factor reduction, cancellations)
- **Performance during shock**: Queue buildup, gate utilization, traveler stranding
- **Recovery**: Time to return to near-baseline throughput (e.g., ≥90% of pre-shock levels)

The model does **not** optimize for resilience; it simulates behavior under shocks to *measure* resilience metrics.

### 1.2 Queueing and Capacity

The airport is modeled as a **capacity-constrained queueing system**:

- **Demand**: Flights arrive stochastically (scheduled each step via `flights_per_step`)
- **Supply**: Runway slots per step, reduced by weather (capacity factor)
- **Bottlenecks**: Runway (primary), gates (secondary), taxi times (delay)

When demand exceeds effective capacity, queues grow. Recovery depends on how quickly the system can drain accumulated queues after the shock ends.

### 1.3 Agent-Based Modeling Rationale

ABM is used because:

- **Heterogeneity**: Flights have different airlines, passenger counts, and states; travelers have different itineraries
- **Interactions**: Flights compete for runway slots and gates; travelers depend on flight completion
- **Emergence**: Queue buildup, gate congestion, and recovery time emerge from individual agent behaviors rather than being prescribed

---

## 2. Assumptions

### 2.1 Temporal and Spatial

| Assumption | Description |
|------------|-------------|
| **Discrete time** | One step = one operational cycle. No explicit mapping to real time (e.g., minutes). |
| **Abstract space** | No geographic layout. Queues, terminal, and gates are conceptual; no spatial coordinates. |
| **Synchronized steps** | All agents act in a fixed order each step (schedule → weather → flights → airport → travelers → collect). |

### 2.2 Demand and Scheduling

| Assumption | Description |
|------------|-------------|
| **Exogenous demand** | Flight count per step is drawn from `{floor(flights_per_step), floor(flights_per_step)+1}` with weights. No feedback from queues or delays. |
| **50/50 arrivals/departures** | Each new flight is arrival or departure with probability 0.5. |
| **No scheduling optimization** | Flights are created and queued immediately; no strategic delay or rescheduling. |
| **Passenger count** | Uniform random in `[passengers_per_flight[0], passengers_per_flight[1]]` (default 80–150). |

### 2.3 Runway and Weather

| Assumption | Description |
|------------|-------------|
| **Slots as capacity** | Runway capacity = `runway_slots_per_step` (default 5). Each slot handles one landing or one takeoff. |
| **Weather only affects runway** | Capacity factor scales runway slots only. Gates, taxiways, and terminal are not weather-affected. |
| **Deterministic shock** | Storm starts at `shock_at_step`, lasts `shock_duration` steps, then clears. No stochastic shock onset. |
| **Minor background variation** | When not in shock, weather may randomly vary among CLEAR, LIGHT_RAIN, WIND with probability `normal_variation_prob` (0.02). |

### 2.4 Gates and Airlines

| Assumption | Description |
|------------|-------------|
| **Airline-specific gates** | Gates are partitioned by airline (e.g. 70, 15, 15). Flights only use gates of their airline. |
| **No gate sharing** | One flight per gate; no simultaneous use. |
| **FIFO within airline** | Gate assignment is first-come-first-served within each airline’s pool (first available gate returned). |
| **No reallocation** | Gates are not reassigned between airlines during a run. |

### 2.5 Flights and Travelers

| Assumption | Description |
|------------|-------------|
| **Fixed taxi/board times** | `taxi_in_steps`, `taxi_out_steps`, `disembark_steps`, `board_steps` are constants (default 3 each). |
| **No rebooking** | Cancelled flights do not create replacement flights; travelers remain linked to cancelled flights. |
| **Departure travelers pre-existing** | Departure passengers are created with `entered_terminal_at = step - random(1, 20)`; they are assumed to have been in the terminal before the flight was scheduled. |
| **No terminal capacity constraint** | `terminal_capacity` is collected but not enforced; travelers are not rejected. |

### 2.6 Agent Behavior

| Assumption | Description |
|------------|-------------|
| **No adaptation** | Flights and travelers follow fixed rules; no learning or strategy change. |
| **No prediction** | Decisions use current state only; no look-ahead. |
| **Cancellation is exogenous** | Each active flight has probability `cancel_probability()` of being cancelled each step; no strategic cancellation. |

---

## 3. Implementation Explanation

### 3.1 Model Architecture

The model is implemented in Python using **Mesa**. Key components:

- **AirportABM** (`model/abm.py`): Main model; holds weather, airport, flights, travelers, scheduler, step runner, and data collector.
- **StepRunner** (`model/step_runner.py`): Defines the order of operations each step.
- **FlightScheduler** (`model/flight_scheduler.py`): Creates new flights and travelers each step.
- **Config** (`config/schema.py`, `config/defaults.py`): All parameters in dataclasses with generic defaults.

### 3.2 Step Order (One Time Step)

Each step executes in this order:

1. **Schedule flights** – Create new flights and travelers; arrivals join arrival queue; departures wait for gate.
2. **Update weather** – Start/end shock or apply minor stochastic variation.
3. **Step flights** – Each flight (not COMPLETED/CANCELLED) runs `Flight.step()`: cancellation check, gate request, taxi, disembark/board.
4. **Airport operations** – Allocate runway slots to arrival/departure queues; serve flights; update `flights_completed_this_step`, `flights_cancelled_this_step`.
5. **Step travelers** – Each traveler updates state based on linked flight status.
6. **Data collection** – Model reporters record throughput, queues, weather, travelers, gates.

### 3.3 Throughput

**Definition**: Number of flights that successfully complete (land or take off) in a given step.

- **flights_completed**: Count of flights that land or take off this step (from `airport.flights_completed_this_step`).
- **flights_cancelled**: Count of flights that were in a queue but were cancelled when served (also incremented in `airport.step()`).

Throughput is limited by `effective_slots = max(1, floor(runway_slots_per_step × capacity_factor))`. Each slot serves one flight from either the arrival or departure queue.

### 3.4 Queues

**Arrival queue**: Flights that have requested landing and are waiting for a runway slot. FIFO.

**Departure queue**: Flights that have completed taxi-out and requested takeoff; waiting for a runway slot. FIFO.

Queue selection when both are non-empty: arrival is chosen if the departure queue is empty, or if `len(arrival_queue) >= len(departure_queue)`, or with probability 0.5. This balances arrivals and departures.

### 3.5 Capacity Factor

**Definition**: Weather-based multiplier on runway capacity, in [0, 1].

- **1.0** = full capacity (clear)
- **0.0** = no operations

From `agents/weather_constants.py`:

| Condition   | Capacity factor |
|-------------|-----------------|
| CLEAR       | 1.0             |
| LIGHT_RAIN  | 0.85            |
| HEAVY_RAIN  | 0.6             |
| FOG         | 0.5             |
| WIND        | 0.7             |
| STORM       | 0.2             |

During a storm, effective slots drop to 20% of nominal capacity.

### 3.6 Flight Lifecycle

**Arrivals**:
```
SCHEDULED → (immediately) IN_QUEUE → (served by runway) LANDED → TAXIING_IN → AT_GATE → COMPLETED
```
- Created and `request_landing()` called → join arrival queue.
- When served: state = LANDED; next step starts taxi-in.
- Taxi-in: `taxi_in_remaining` decremented; when 0, request gate.
- At gate: `gate_occupancy_remaining` (disembark) decremented; when 0, release gate, COMPLETED.

**Departures**:
```
SCHEDULED → (gate assigned) AT_GATE → (board done) TAXIING_OUT → (taxi done) IN_QUEUE → (served) COMPLETED
```
- Created but do *not* request takeoff immediately.
- `Flight.step()`: request gate for airline; when assigned, AT_GATE with `gate_occupancy_remaining = board_steps`.
- When board done: release gate, TAXIING_OUT.
- When taxi-out done: `request_takeoff()` → join departure queue.
- When served by runway: COMPLETED.

**Cancellation**: Any flight in IN_QUEUE, EXECUTING, LANDED, TAXIING_IN, AT_GATE, or TAXIING_OUT can be cancelled each step with probability `weather.cancel_probability()`. If it had a gate, the gate is released.

### 3.7 Gate Allocation

- **GatePool** (`agents/gate.py`): Partitions gates by airline. `request_gate(airline_id)` returns the first available gate for that airline, or `None`.
- **Blocking**: A departure in SCHEDULED cannot proceed until it gets a gate. If no gate is free for its airline, it waits (retries next step).
- **Occupancy**: A gate is occupied for `disembark_steps` (arrival) or `board_steps` (departure) steps.

### 3.8 Traveler Lifecycle

**States**: INBOUND, IN_TERMINAL, OUTBOUND, EXITED.

- **INBOUND**: Linked to an arrival flight. When flight COMPLETED → IN_TERMINAL, `entered_terminal_at = step`. When flight CANCELLED → `total_wait_steps += 1` (stranded inbound; model does not explicitly track this as a separate state).
- **IN_TERMINAL**: Linked to a departure flight. When flight COMPLETED → EXITED. When flight CANCELLED → `total_wait_steps += 1`; traveler remains IN_TERMINAL with cancelled departure = **stranded**.
- **Stranded** (`metrics/collectors.py`): `state == IN_TERMINAL` and `departure_flight.state == CANCELLED`.

Departure travelers are created with `entered_terminal_at = step - random(1, 20)` to represent time already spent in the terminal.

### 3.9 Weather and Shocks

- **WeatherAgent** (`agents/weather.py`): Holds `condition` (enum), `shock_at_step`, `shock_duration`.
- **Shock start**: When `steps == shock_at_step`, `condition = STORM`.
- **Shock end**: When `_steps_in_shock >= shock_duration`, `condition = CLEAR`.
- **Normal variation**: When not in shock, with probability 0.02, condition randomly set to CLEAR, LIGHT_RAIN, or WIND.

### 3.10 Resilience Metrics (Post-Run)

Computed in `metrics/resilience.py` from the time-series DataFrame:

| Metric | Definition |
|--------|------------|
| **baseline_throughput** | Mean `flights_completed` per step in pre-shock period |
| **during_shock_throughput** | Mean `flights_completed` during shock |
| **throughput_drop_ratio** | `1 - (during_shock / baseline)` |
| **recovery_step** | First step after shock where `flights_completed >= 0.9 × baseline` |
| **recovery_time_steps** | `recovery_step - shock_end_step` |
| **max_arrival_queue_during_shock** | Max arrival queue length during shock |
| **max_departure_queue_during_shock** | Max departure queue length during shock |
| **max_travelers_in_terminal** | Peak travelers in terminal over run |
| **stranded** | Travelers in terminal with cancelled departure (collected each step as `travelers_stranded`) |

### 3.11 Default Configuration

From `config/schema.py` and `config/defaults.py`:

- **n_steps**: 200
- **flights_per_step**: 2.5
- **runway_slots_per_step**: 5
- **n_gates**: 100
- **gates_per_airline**: (70, 15, 15)
- **airline_flight_share**: (0.8, 0.1, 0.1)
- **taxi_in_steps, taxi_out_steps, disembark_steps, board_steps**: 3 each
- **shock_at_step**: 60
- **shock_duration**: 12

---

## 4. Summary

The Airport Resilience ABM simulates airport operations under weather shocks using a capacity-constrained queueing framework. Flights and travelers are agents with fixed rules; throughput, queues, gate utilization, and stranding emerge from their interactions. The model is parsimonious (no learning, no optimization, abstract space) and designed for resilience analysis: measuring absorption, performance during shock, and recovery time.

For the full ODD (Overview, Design concepts, Details) protocol, see [ODD.md](../ODD.md).

---

## 5. Horton Critical Functions and KPIs

The model tracks KPIs aligned with Horton's critical functions (Table 2-1):

| Horton CF | Critical Function | KPIs in Model |
|-----------|-------------------|---------------|
| **cf1** | Facilitate and support airport landings and takeoffs | Throughput, throughput efficiency, queue imbalance |
| **cf2** | Provide emergency support services during disruptions | Stranded travelers, stranding proportion, traveler exit rate |
| **cf3** | Provide intra-airport transportation | Travelers in terminal (proxy for passenger load) |
| **cf4** | Support and maintain intra-airport communication systems | Queue imbalance (proxy for coordination) |

**Additional Horton-aligned KPIs** (plotted in `plot_kpis`):

1. **Throughput efficiency** (cf1): `flights_completed / effective_slots`. Ratio of actual throughput to weather-reduced capacity. Near 1.0 when runway slots are fully used; <1 when demand-limited or queues empty.
2. **Queue imbalance** (cf1/cf4): `|arrival_queue − departure_queue|`. Large imbalance may indicate coordination issues between arrival and departure flows.
3. **Stranding proportion** (cf2): `travelers_stranded / travelers_in_terminal × 100%`. Share of terminal travelers whose departure was cancelled; reflects passenger safety during disruptions.
4. **Traveler exit rate** (cf2): Travelers who exited the terminal this step. Operational continuity from the passenger perspective.
