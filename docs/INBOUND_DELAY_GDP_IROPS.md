# Phase B: inbound delay, Ground Delay Program (GDP), airline IROPS

This phase separates **capacity constraints** (weather / ATC) from **airline cancellation** decisions, and adds late inbound aircraft.

## Roles (industry alignment)

| Actor | Role in this model |
|-------|--------------------|
| **Weather / airport capacity** | Reduces runway **acceptance rate** via capacity factor |
| **ATC — Ground Delay Program (GDP)** | When capacity is low, assigns **EDCT** (Expect Departure Clearance Time) so departures hold on the ground |
| **Airline Operations Control (AOC) — IROPS** | Cancels flights when projected delay exceeds a threshold; airports do not “cancel flights” |

## Inbound delay (ETA vs STA)

- **STA**: Scheduled Time of Arrival (`scheduled_time_step` on arrivals)
- **ETA**: Estimated Time of Arrival (`eta_step` = STA + inbound delay)
- Inbound delay is drawn (optional lognormal) with `inbound_delay_prob` and `inbound_delay_mean_steps`
- The arrival requests landing when the simulation step reaches **ETA**, not STA

Late inbound aircraft push **on-block** later → **minimum ground time (MGT)** starts later → outbound **STD** may be missed (delay propagation on the rotation).

## Ground Delay Program (GDP)

- Active when `weather.capacity_factor() <= gdp_capacity_threshold` (default 0.7)
- After taxi-out, a departure receives an **EDCT** and joins the departure queue only when `step >= EDCT`
- Time-series columns: `gdp_active`, `edcts_assigned`, `flights_held_for_edct`

## Airline IROPS cancellations

- Module: `agents/airline_ops.py` (`AirlineOperationsControl`)
- Prefer cancelling departures still **SCHEDULED** or **AT_GATE** over flights already in the runway queue
- Threshold: `irops_cancel_delay_threshold_steps` (default 15)
- Cap: `irops_max_cancels_per_step`
- Cancel reason: `CancelReason.AIRLINE_IROPS`
- If an inbound leg is cancelled before completion, the paired outbound on the same registration is cancelled (no aircraft for the rotation)
- Random weather Bernoulli cancellations on individual flights were **removed**

## Configuration

```json
{
  "inbound_delay_enabled": true,
  "inbound_delay_prob": 0.4,
  "inbound_delay_mean_steps": 2.0,
  "gdp_enabled": true,
  "gdp_capacity_threshold": 0.7,
  "irops_enabled": true,
  "irops_cancel_delay_threshold_steps": 15,
  "irops_max_cancels_per_step": 2
}
```

## Step order

1. Activate schedule / inject demand (STA / ETA / STD)  
2. Weather (capacity)  
3. Ground Delay Program (GDP)  
4. Airline Operations Control (IROPS)  
5. Flight progress (taxi, gate, EDCT hold)  
6. Airport runway slots  
7. Travelers  
8. Metrics  

## Implementation map

| File | Responsibility |
|------|----------------|
| `model/inbound_delay.py` | Draw inbound delay steps |
| `agents/ground_delay_program.py` | GDP active flag + EDCT |
| `agents/airline_ops.py` | Airline IROPS cancel policy |
| `agents/cancel_reason.py` | `AIRLINE_IROPS` |
| `model/step_runner.py` | Step order above |

Next (Phase C): preferential / common-use **gate allocation**, gate class compatibility, remote stands.
