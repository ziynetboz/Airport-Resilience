# Airport Resilience ABM — Realism Gap Analysis

**Date:** 2026-10-06  
**Scope:** Review of current model vs. industry practice for airport operations, delays, gates, cancellations, passenger/baggage flows, and resilience analysis.  
**Evidence:** Code review (`agents/`, `model/`, `config/`) plus a seeded default run (seed=42, shock at 60 for 12 steps).

---

## Executive verdict

The model is a solid **runway–queue resilience skeleton** (weather → capacity → queues → throughput → recovery). It is **not yet an operations model**. Under defaults, demand is light relative to capacity (mean gate utilization ≈ 7%, arrival queues near empty), so many bottlenecks you care about barely appear. The highest-value next modules are: **(1) published schedule + aircraft turnarounds**, **(2) inbound delay / irregular ops**, **(3) airline-driven cancellation & recovery**, **(4) industry gate allocation rules**, then **(5) baggage / ground handling** as delay amplifiers—not as the first priority.

---

## Baseline diagnostics (default config)

| Metric | Value (seed 42) | Implication |
|--------|-----------------|-------------|
| Arrivals / departures scheduled | 252 / 253 | 50/50 mix is fine; takeoff *count* is not the gap |
| Arrivals / departures completed | 231 / 223 | Slight departure lag from longer pipeline (gate→board→taxi→runway) |
| Mean / max gate utilization | 0.07 / 0.12 | Gates are over-provisioned; gate stress will not emerge |
| Mean arr / dep queue | 0.05 / 0.29 | Runway rarely binding outside shock |
| Peak travelers in terminal | ~29.7k | Terminal capacity (5000) is informational only; stock grows without exit for many pax |
| Peak stranded | ~2.5k | Driven by random weather cancellations, not airline IROPS logic |

**On “do we need more takeoffs?”**  
**No — not as a simple increase in departure share.** Scheduled arrivals and departures are already balanced. Departures reach the runway later because they must win a gate, board, and taxi out first. During capacity shocks that structural lag can look like “not enough takeoffs,” but the fix is **turnaround linking, gate dwell realism, and slot/queue policy**—not raising the departure probability above 0.5. If anything, calibrate **demand intensity** (`flights_per_step`) or **gate count** so utilization sits in a realistic band (often 50–80% peak for constrained terminals), rather than forcing more departures.

---

## Answers to your specific questions

### 1. More takeoffs?

Confirm: **scheduled A/D mix is adequate**. Real airports match arrivals and departures over the day because of **aircraft rotations**. Your model creates arrivals and departures as independent Poisson draws, so aircraft balance, overnight parking, and “arrival that becomes the next departure” are missing. Prefer:

- Aircraft agents with turnaround: `arrive → ground service → depart`
- Optional diurnal schedule banks (morning outbound, evening inbound) instead of flat 50/50 every step

### 2. Gate allocation — industry best practice

Current behavior: exclusive airline pools, first free gate in list, no sharing, no aircraft–gate compatibility, no reallocation under disruption.

Industry practice to encode (preferential + common-use hybrids):

| Practice | What to model |
|----------|----------------|
| **Preferential / leased gates** | Airline has first rights on a set of gates (you already have exclusive pools) |
| **Common-use / CUTE / CUPPS** | Overflow pool usable by any airline when preferred gates are full |
| **Compatibility** | Gate class (narrowbody / widebody / international / hardstand); reject incompatible assignments |
| **Buffer / tow rules** | Minimum gate buffer between flights; tow-to-remote if gate needed for priority |
| **Priority under IROPS** | International / long-haul / high-load / connecting banks preferred over short-haul |
| **Adjacency / walking** | Soft cost: keep airline banks contiguous; minimize passenger walk for connections |
| **Remote stands** | Extra capacity with bus transfer time penalty (extends taxi/disembark) |
| **Dynamic reallocation** | Temporary gate borrow between airlines with consent / airport authority override |

**Recommended algorithm sketch (airside ops):**

1. Build a **desired schedule** of gate occupancy intervals (scheduled in/out + buffers).  
2. Assign preferred gates by airline lease / historical use.  
3. On conflict: try airline’s other gates → common-use → remote stand → hold / delay departure or arrival.  
4. Under storm/GDP: freeze new preferential claims; run a **disruption allocator** (priority queue by priority class + number of connecting pax).  
5. Record **gate hold**, **tow**, and **assignment failure** as KPIs.

Document this policy in config (not hard-coded) so you can compare exclusive vs hybrid common-use resilience.

### 3. Flights landing already delayed

Today every arrival is created at `scheduled_step` and immediately joins the landing queue—**no inbound lateness**, no airborne holding, no diversion.

Add:

- `scheduled_arrival_step` vs `actual_arrival_ready_step` with a delay distribution (lognormal or empirical; causes: late aircraft, weather en-route, ATC)  
- **Ground Delay Program (GDP) / Airspace Flow Program**: reduce `effective_slots` and/or hold departures at origin (for your single-airport model: delay when flights become “ready”)  
- **Holding / diversion**: if arrival queue or weather exceeds thresholds, divert (remove flight + mark connecting pax impacted) or hold with fuel/time cost  
- Propagate delay into gate conflict and turnaround (late in → late out)

This is among the highest-leverage realism upgrades for resilience studies.

### 4. Who cancels — airport vs airline?

Correct intuition: **airports rarely “cancel flights”; airlines cancel (or consolidate) under irregular operations**, often under ATC slot constraints and crew/aircraft legality.

Current model: each active flight draws an independent Bernoulli cancel from weather (`WEATHER_CANCEL_PROB`). That conflates environment with operator decision and cancels mid-taxi / at-gate unrealistically often.

Better split:

| Actor | Decision |
|-------|----------|
| **Weather / ATC (airport & ANS)** | Capacity factor, slot programs, ground stops, runway config |
| **Airline operations control (AOC)** | Cancel / delay / swap aircraft / rebook based on cost, crew, connections, curfew |
| **Airport authority** | Gate policy, terminal limits, emergency declaration—not flight cancellation per se |

Suggested cancel model:

- Weather reduces capacity → queues / delays grow  
- Airline cancels when projected delay > threshold, or aircraft/crew illegal, or bank integrity requires cutting thin spokes  
- Prefer cancelling **departures still at gate** over airborne/taxiing flights  
- Optional: cancel-and-reaccommodate creates replacement flights later (recovery schedule)

### 5. Schedule vs simulator

You currently have a **generator**, not a **schedule**:

- Stochastic `flights_per_step` with no published timetable  
- No feedback from congestion to demand  
- No banks, banks of connections, or time-of-day peaks  

Recommended architecture:

1. **Schedule layer (input):** list of flights with `flight_id`, airline, type, scheduled times, aircraft_id, seats, origin/dest (optional), preferred gate class.  
2. **Simulator layer:** executes readiness, resources, delays; produces actual times and states.  
3. **KPIs:** on-time performance (OTP15), average delay, schedule recovery time, completed vs scheduled in window.

Keep the stochastic generator as a **synthetic schedule builder** for experiments, but drive the ABM from an explicit schedule object so “planned vs actual” is first-class.

### 6. People vs gate availability

Today `passenger_count` only creates Traveler agents; it does **not** affect gate occupancy time, boarding rate, or gate eligibility. Terminal capacity is not enforced. Arrival travelers often never get a departure link, so terminal stock explodes.

Industry-aligned coupling:

- **Seat capacity / load factor** → boarding and disembark duration (stochastic, size-dependent)  
- **Aircraft type ↔ gate type**  
- **Connecting passengers** with MCT (minimum connection time); missed connections → stranded / rebook  
- **Terminal capacity / LOI (level of service):** enforce or soft-penalize overcrowding (dwell, security queue proxy)  
- Gate availability should be driven by **turnaround occupancy**, not passenger headcount alone—but headcount modulates **dwell time** and **missed-connection risk**

### 7. Luggage / baggage handling module

Worth adding **after** turnaround + inbound delay + cancel logic, because baggage primarily **amplifies** those failures:

- Transfer bags: arrival flight → bag room / sorter → departure flight; late inbound ⇒ misconnect  
- Local bags: check-in → make-up → load; security/screening surge under shock  
- Arrival claim: carousel capacity; delayed unload extends gate dwell if belt not ready (optional coupling)  
- KPIs: mishandled bag rate, transfer success, bag-induced departure delay  

A minimal useful module: bag batches tied to flights with transfer deadlines; failed transfers increment stranded/rebook and can delay departure pushback.

---

## Additional gaps you should consider

Prioritized for **resilience accuracy** (not feature completeness):

### P0 — Changes that reshape dynamics

1. **Aircraft turnaround / rotation** — Link arrival aircraft to next departure; ground time = max(passenger, bags, fuel, clean, crew). This fixes A/D balance structurally and creates realistic gate dwell.  
2. **Explicit schedule + OTP metrics** — Planned vs actual; recovery of the timetable after shock.  
3. **Airline IROPS decision layer** — Delay vs cancel vs aircraft swap; airport supplies capacity, airline decides cuts.  
4. **Inbound delay & ATC flow programs** — GDP/GS/holding/diversion.  
5. **Demand calibration** — Raise operational intensity or shrink gates so runway/gates bind in baseline; otherwise resilience curves understate bottlenecks.

### P1 — Strong realism for gates, pax, disruption

6. **Hybrid gate policy** (preferential + common-use + remote stands + compatibility).  
7. **Connecting passengers + MCT + rebooking**.  
8. **Enforce or soft-constrain terminal capacity**; add simple security/landside queue if passenger stranding is a resilience KPI.  
9. **Stochastic process times** (taxi, board, disembark as distributions; weather multiplies taxi/ground too—not only runway slots).  
10. **Runway configuration / arrival–departure capacity split** (e.g., preferential landing under low ceiling) instead of a single shared slot pool with ad-hoc 50/50 rule.

### P2 — Richer operations / baggage / network

11. **Baggage handling & transfer failures**.  
12. **Crew legality / maintenance** (optional; drives many real cancellations).  
13. **Curfew / night noise / slot coordination (IATA Level 3)**.  
14. **Multi-airport or feeder delay import** (external delay as exogenous process).  
15. **Spatial/taxiway network** (only if congestion on taxi is a study target; expensive relative to value for many resilience questions).  
16. **Emergency services / CF2** beyond stranded counts (currently a weak proxy).

---

## Mapping: current assumptions → recommended replacement

| Current assumption | Limitation | Recommended component |
|--------------------|------------|------------------------|
| 50/50 independent A/D draws | No aircraft balance | Turnaround-linked flights |
| Exclusive airline gates, FIFO first free | No common-use, no compatibility | Preferential + overflow + gate class |
| Cancel = weather Bernoulli on many states | Airports don’t cancel that way | Capacity shock + airline cancel policy |
| Arrival ready immediately | No propagated delay | Inbound delay + GDP/holding |
| Fixed taxi/board/disembark steps | No variability / weather on ground | Stochastic times; weather multipliers |
| `terminal_capacity` unused | Pax stock unconstrained | Enforce LoS / capacity; connections |
| Pax only tied to one flight | No misconnect dynamics | Connecting itineraries + MCT |
| No bags | Misses transfer-driven delays | Baggage batch agent / submodel |
| Generator demand | No schedule recovery KPI | Schedule object + OTP / recovery |
| Weather affects runway only | Understates storm impact | Also scale taxi, turnaround, ramp |

---

## Suggested module roadmap (implementation order)

```
Phase A  Schedule + AircraftTurnaround + OTP metrics — **implemented** (see `docs/PUBLISHED_SCHEDULE_AND_OTP.md`)
Phase B  InboundDelay + ATCFlowProgram + AirlineCancel/Recover — **implemented** (see `docs/INBOUND_DELAY_GDP_IROPS.md`)
Phase C  GateAllocator (preferential/common-use/remote/compatibility) — **implemented** (see `docs/GATE_ALLOCATION.md`)
Phase D  Connections (MCT) + terminal LoS — **implemented** (see `docs/CONNECTIONS_MCT_TERMINAL_LOS.md`)
Phase E  BaggageHandling (transfer + make-up + claim) — **implemented** (see `docs/BAGGAGE_HANDLING.md`)
Phase F  Optional: taxiway network, crew, curfew, multi-airport delay import
```

Each phase should keep parameters in `config/schema.py`, wire into `StepRunner` order, and add reporters in `metrics/` (e.g., OTP15, gate conflict rate, cancel reason mix, bag misconnect rate, turnaround delay attribution).

---

## Step-order hint once modules exist

A realistic step becomes:

1. Publish/advance schedule readiness (including inbound delays / GDP)  
2. Weather + ATC capacity  
3. Airline decisions (cancel / delay / swap)  
4. Gate allocator (assignments, tows, remote)  
5. Ground handling + baggage  
6. Flight airside progress (taxi, runway queues)  
7. Passenger state (connections, stranding, rebook)  
8. Metrics  

---

## What not to overbuild first

- Full spatial terminal digital twin  
- Detailed fuel/catering animations without turnaround critical path  
- More departure draws without turnarounds  
- Bag module before cancel/delay/turnaround logic (bags need those events to matter)

---

## Summary checklist

| Your topic | Verdict |
|------------|---------|
| More takeoffs? | **Not as higher departure share**; add turnarounds and calibrate intensity |
| Gate allocation explanation / best practice | **Yes — document & implement preferential + common-use + compatibility + IROPS priority** |
| Flights landing already delayed | **Yes — high priority** |
| Airport vs airline cancel | **Yes — split capacity (airport/ATC) from cancel decisions (airline)** |
| Schedule vs simulator | **Yes — explicit schedule + actuals + OTP** |
| People vs gate availability | **Couple via turnaround dwell, aircraft/gate class, connections—not raw headcount alone** |
| Luggage module | **Yes, but Phase E**; ties delays to transfer failures |
| Anything else? | Turnaround, ATC flow programs, stochastic ground times, weather on ramp/taxi, terminal LoS, runway A/D capacity split, rebooking |

This document is advisory; implementation can proceed phase-by-phase against the roadmap above.
