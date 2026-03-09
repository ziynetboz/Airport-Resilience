# ODD Protocol: Airport Resilience ABM

**Model Name:** Airport Resilience Agent-Based Model  
**Version:** 1.1  
**Reference:** Grimm et al. (2010, 2020) ODD Protocol for describing individual- and agent-based models

---

## 1. Overview

### 1.1 Purpose

The Airport Resilience ABM is designed to study **airport operational resilience** under **weather-driven shocks** (natural systems). The model simulates runway operations (landings and takeoffs), **taxi times**, **gate assignments by airlines**, **gate availability**, traveler flows through the terminal, and environmental conditions. The primary purpose is to analyze how throughput, queue lengths, gate utilization, and traveler stranding respond during and after a shock event (e.g., a storm), and to compute resilience metrics such as throughput drop, recovery time, and peak queues.

### 1.2 Entities, state variables, and scales

**Entities**

| Entity | Type | Description |
|--------|------|-------------|
| **WeatherAgent** | Agent | Governs weather condition and shock events; provides capacity factor and cancellation probability for the airport |
| **Airport** | System / Environment | Runway, terminal, and gate pool; maintains arrival/departure queues; allocates runway slots and gates |
| **Gate** | Resource | Single gate assigned to an airline; can be occupied by one flight |
| **GatePool** | System | Manages gates partitioned by airline; flights request gates from their airline |
| **Flight** | Agent | Arrival or departure; passes through taxi, gate occupancy, and runway queues (see state variables) |
| **Traveler** | Agent | A passenger linked to arrival and/or departure flights; tracks state (inbound, in terminal, exited) and stranded status |
| **FlightScheduler** | Process | Creates new flights and travelers each step based on configurable rates |

**State variables**

- **WeatherAgent:** `condition` (CLEAR, LIGHT_RAIN, HEAVY_RAIN, FOG, WIND, STORM), `shock_at_step`, `shock_duration`, `_steps_in_shock`
- **Airport:** `runway_slots_per_step`, `terminal_capacity`, `gate_pool`, `taxi_in_steps`, `taxi_out_steps`, `disembark_steps`, `board_steps`, `arrival_queue`, `departure_queue`, `flights_completed_this_step`, `flights_cancelled_this_step`
- **Gate:** `gate_id`, `airline_id`, `occupied_by` (Flight or None)
- **Flight:** `flight_type` (ARRIVAL, DEPARTURE), `airline_id`, `state` (SCHEDULED, IN_QUEUE, EXECUTING, LANDED, TAXIING_IN, AT_GATE, TAXIING_OUT, COMPLETED, CANCELLED), `scheduled_step`, `queued_at_step`, `completed_at_step`, `cancelled_at_step`, `passenger_count`, `assigned_gate`, `taxi_in_remaining`, `taxi_out_remaining`, `gate_occupancy_remaining`
- **Traveler:** `state` (INBOUND, IN_TERMINAL, OUTBOUND, EXITED), `arrival_flight`, `departure_flight`, `entered_terminal_at`, `exited_at`, `total_wait_steps`

**Scales**

- **Temporal:** Discrete time steps (no explicit physical time unit; one step represents one operational cycle)
- **Spatial:** Abstract; no explicit spatial representation (queues and terminal are conceptual)
- **Agent counts:** Flights and travelers are created dynamically; typical run has hundreds of flights and thousands of travelers

### 1.3 Process overview and scheduling

Each time step executes in the following order:

1. **Schedule flights** – FlightScheduler creates flights (each assigned an airline); arrivals request landing; departures wait for gate
2. **Update weather** – WeatherAgent updates condition (start/end shock at configured steps; otherwise stochastic variation)
3. **Step flights** – Flights: check cancellation; departures in SCHEDULED request gate; arrivals in LANDED taxi in; flights at gate complete disembark/board; departures taxi out then request takeoff
4. **Airport operations** – Allocate runway slots to arrival/departure queues; arrivals that land transition to LANDED (taxi in, gate, disembark); departures that take off are COMPLETED
5. **Step travelers** – Each Traveler updates state based on arrival/departure flight status
6. **Data collection** – Model reporters record throughput, queues, weather, travelers, gates available

---

## 2. Design concepts

### 2.1 Design principles

The model prioritizes simplicity and parsimony: minimal entities and rules to capture the core dynamics of airport throughput under weather shocks. It is implemented in Python using the Mesa ABM framework, with clear separation of config, agents, model, and metrics.

### 2.2 Emergence

- **Queue buildup** emerges from flight scheduling rate, runway capacity, gate availability, taxi times, and weather-induced capacity reduction
- **Gate congestion** emerges when many flights need gates simultaneously; departures may wait in SCHEDULED until a gate is free
- **Recovery time** (steps to return to ≥90% baseline throughput) emerges from shock duration, queue lengths, gate/taxi bottlenecks, and post-shock capacity restoration
- **Traveler stranding** emerges when departure flights are cancelled while travelers are in the terminal

### 2.3 Adaptation

Agents do not adapt strategies. Flights and travelers follow fixed rules. The Airport does not change capacity or policies. Weather follows a predetermined shock schedule (optional) plus minor stochastic variation.

### 2.4 Objectives

- **Flights:** Implicit objective to land or take off; no explicit optimization
- **Travelers:** Implicit objective to exit (complete journey); no explicit optimization
- **WeatherAgent:** No objectives; merely represents environmental conditions

### 2.5 Learning

No learning. All behavior is rule-based and static.

### 2.6 Prediction

Agents do not predict future states. Decisions are based on current state only.

### 2.7 Sensing

- **WeatherAgent:** Reads model step number to trigger shock start/end
- **Airport:** Reads weather capacity factor and cancel probability; inspects queue lengths
- **Flight:** Reads weather cancel probability; knows its own state and queue position
- **Traveler:** Senses arrival/departure flight state (completed, cancelled)

### 2.8 Interaction

- **WeatherAgent → Airport:** Provides capacity factor and cancel probability
- **FlightScheduler → Airport:** Requests landing for arrivals; departures request gate via Flight.step
- **Flight → WeatherAgent:** Flight checks cancel probability each step
- **Flight → Airport/GatePool:** Flights request and release gates (by airline); request takeoff after taxi-out
- **Airport → Flight:** Serves runway queues; arrivals transition to LANDED; departures to COMPLETED
- **Traveler → Flight:** Traveler state depends on linked flight completion/cancellation

### 2.9 Stochasticity

- **Flight count:** Number of new flights per step drawn from `[floor(flights_per_step), floor(flights_per_step)+1]` with weights
- **Flight type:** Each new flight is arrival or departure with probability 0.5
- **Airline assignment:** Each flight assigned `airline_id` via `airline_flight_share` weights (e.g. default 80%, 10%, 10% for 3 airlines)
- **Passenger count:** Uniform random in `[passengers_per_flight[0], passengers_per_flight[1]]`
- **Departure traveler entry:** `entered_terminal_at` set to `step - random(1, 20)` for departures
- **Weather:** With probability `normal_variation_prob`, condition randomly changes among CLEAR, LIGHT_RAIN, WIND (when not in shock)
- **Flight cancellation:** Each active flight has probability `cancel_probability()` of being cancelled (weather-dependent)
- **Queue selection:** When both queues non-empty, arrival chosen with probability 0.5 or when arrival queue ≥ departure queue

### 2.10 Collectives

- **Arrival queue** and **departure queue** are collectives of flights; Airport serves from these in FIFO order
- **Gates** are partitioned by airline via `gates_per_airline` (e.g. default 70, 15, 15); flights request from their airline's pool
- **Travelers in terminal** are a collective; metrics aggregate counts (in terminal, stranded)

---

## 3. Details

### 3.1 Initialization

At step 0:

- **WeatherAgent:** Created with `condition = CLEAR`; `shock_at_step` and `shock_duration` from config
- **Airport:** Created with runway, terminal, gate pool (`n_gates`, `n_airlines`), taxi/gate timing; empty queues
- **Flights:** Empty list
- **Travelers:** Empty list
- **Model:** `steps = 0`; seed set for reproducibility

The first scheduling and stepping occur from step 1 onward.

### 3.2 Input data

| Parameter | Description | Default |
|-----------|-------------|---------|
| `n_steps` | Number of simulation steps | 200 |
| `flights_per_step` | Mean new flights per step | 2.0 |
| `passengers_per_flight` | (min, max) passengers per flight | (80, 150) |
| `runway_slots_per_step` | Runway capacity (slots) per step | 5 |
| `terminal_capacity` | Terminal capacity (informational) | 5000 |
| `n_gates` | Total number of gates | 100 |
| `n_airlines` | Number of airlines | 3 |
| `gates_per_airline` | Gates per airline, e.g. (70, 15, 15) | (70, 15, 15) |
| `airline_flight_share` | Flight probability per airline, e.g. (0.8, 0.1, 0.1) | (0.8, 0.1, 0.1) |
| `taxi_in_steps` | Steps to taxi from runway to gate (arrivals) | 3 |
| `taxi_out_steps` | Steps to taxi from gate to runway (departures) | 3 |
| `disembark_steps` | Steps at gate for disembarking (arrivals) | 3 |
| `board_steps` | Steps at gate for boarding (departures) | 3 |
| `shock_at_step` | Step at which storm starts | 60 |
| `shock_duration` | Duration of storm (steps) | 12 |
| `seed` | Random seed | configurable |

Weather capacity factors (by condition): CLEAR 1.0, LIGHT_RAIN 0.85, HEAVY_RAIN 0.6, FOG 0.5, WIND 0.7, STORM 0.2  
Cancellation probabilities: CLEAR 0, LIGHT_RAIN 0.01, HEAVY_RAIN 0.05, FOG 0.03, WIND 0.02, STORM 0.15

### 3.3 Submodels

**3.3.1 Flight scheduling**

- Draw `n_new` from `{floor(flights_per_step), floor(flights_per_step)+1}` with weights `(1 - frac, frac)` where `frac = flights_per_step % 1`
- For each of `n_new` flights: draw arrival (0.5) or departure; draw `airline_id` from `airline_flight_share` weights (e.g. 80%, 10%, 10% for 3 airlines); draw passengers from `uniform(passengers_per_flight[0], passengers_per_flight[1])`
- Create Flight with `airline_id`; add to model
- Arrivals: request landing at Airport (join arrival queue)
- Departures: do not request takeoff; Flight.step will request gate, then taxi out, then request takeoff
- Create Traveler agents: for arrivals, one per passenger with `arrival_flight` set; for departures, one per passenger with `departure_flight` set and `entered_terminal_at = step - random(1, 20)`

**3.3.1a Gate assignment**

- Gates are partitioned among airlines: each airline gets `n_gates // n_airlines` gates
- Flight requests gate from `GatePool.request_gate(airline_id)`; returns first available gate for that airline or None
- If gate assigned: `gate.occupied_by = flight`; flight holds gate until disembark/board complete

**3.3.2 Weather update**

- If `steps == shock_at_step`: set `condition = STORM`
- If in STORM: increment `_steps_in_shock`; if `_steps_in_shock >= shock_duration`: set `condition = CLEAR`
- Else: with probability `normal_variation_prob`, set `condition = random(CLEAR, LIGHT_RAIN, WIND)`

**3.3.3 Flight cancellation**

- For each Flight in IN_QUEUE, EXECUTING, LANDED, TAXIING_IN, AT_GATE, or TAXIING_OUT: if `random() < weather.cancel_probability()`, set `state = CANCELLED`, `cancelled_at_step = steps`; if flight had `assigned_gate`, release it

**3.3.4 Taxi and gate occupancy (Flight.step)**

- **Departure SCHEDULED:** Request gate for airline; if available, assign gate, set `gate_occupancy_remaining = board_steps`, state = AT_GATE
- **Arrival LANDED:** Set `taxi_in_remaining = taxi_in_steps`, state = TAXIING_IN
- **TAXIING_IN:** Decrement `taxi_in_remaining`; when 0, request gate; if available, assign gate, set `gate_occupancy_remaining = disembark_steps`, state = AT_GATE
- **AT_GATE (arrival):** Decrement `gate_occupancy_remaining`; when 0, release gate, state = COMPLETED, `completed_at_step = steps`
- **AT_GATE (departure):** Decrement `gate_occupancy_remaining`; when 0, release gate, set `taxi_out_remaining = taxi_out_steps`, state = TAXIING_OUT
- **TAXIING_OUT:** Decrement `taxi_out_remaining`; when 0, request takeoff (join departure queue)

**3.3.5 Airport slot allocation**

- `effective_slots = max(1, floor(runway_slots_per_step * weather.capacity_factor()))`
- For each slot: if both queues empty, stop; else choose arrival or departure (arrival if departure queue empty, or if arrival queue length ≥ departure queue length, or with probability 0.5); pop from chosen queue
- **Arrival:** If not CANCELLED, set state = LANDED (triggers taxi-in, gate, disembark); increment `flights_completed_this_step`
- **Departure:** If not CANCELLED, set state = COMPLETED, `completed_at_step = steps`; increment `flights_completed_this_step`
- If CANCELLED, increment `flights_cancelled_this_step`

**3.3.6 Traveler state update**

- For INBOUND: if arrival flight COMPLETED → IN_TERMINAL, `entered_terminal_at = steps`; if CANCELLED → `total_wait_steps += 1`
- For IN_TERMINAL: if departure flight COMPLETED → EXITED, `exited_at = steps`, `total_wait_steps += steps - entered_terminal_at`; if departure CANCELLED → `total_wait_steps += 1`
- For OUTBOUND: if departure COMPLETED → EXITED

**3.3.7 Resilience metrics (post-run)**

- Baseline throughput: mean `flights_completed` per step in pre-shock period
- During-shock throughput: mean `flights_completed` during shock
- Throughput drop ratio: `1 - (during_shock / baseline)`
- Recovery step: first step after shock where `flights_completed >= 0.9 * baseline`
- Recovery time: steps from shock end to recovery step
- Max arrival/departure queues during shock
- Max travelers in terminal; stranded travelers (in terminal with cancelled departure)
- `gates_available` collected each step for time-series analysis

---

## References

- Grimm, V., et al. (2010). The ODD protocol: A review and first update. *Ecological Modelling* 221, 2760–2768.
- Grimm, V., et al. (2020). The ODD protocol for describing agent-based and other simulation models: A second update to improve clarity, replication, and structural realism. *Journal of Artificial Societies and Social Simulation* 23(2), 7.
