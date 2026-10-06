# Published flight schedule, aircraft rotations, and OTP

This model supports two demand modes (see `config/schedule_mode.py`):

| Mode | Industry meaning |
|------|------------------|
| **`published`** | Flights follow a **published flight schedule** with **STA** (Scheduled Time of Arrival) and **STD** (Scheduled Time of Departure). Inbound and outbound legs are paired on the same **aircraft registration** (rotation). |
| **`stochastic`** | Legacy Poisson-style injection each step (no published timetable). |

## Aircraft rotation and minimum ground time (MGT)

Each rotation has:

- An **inbound leg** (arrival) with STA at step `scheduled_time_step`.
- An **outbound leg** (departure) with STD at step `scheduled_time_step`.
- **Minimum ground time (MGT)** (`min_ground_time_steps`): elapsed steps after **on-block** (gate arrival complete) before the outbound leg may begin **off-block** (gate boarding).

The outbound leg is released when both `current_step >= STD` and MGT is satisfied after the inbound leg completes at the gate.

## Actual times and delay

| Term | Model field | When set |
|------|-------------|----------|
| **ATA** (Actual Time of Arrival) | `actual_arrival_step` | Inbound leg completes at gate (on-block proxy) |
| **ATD** (Actual Time of Departure) | `actual_departure_step` | Outbound leg receives a runway slot (takeoff) |

Delay vs schedule: `actual_* - scheduled_time_step`.

## On-Time Performance (OTP)

**OTP** is reported in `metrics/otp.py` and in the time series as `otp_arrival_pct` / `otp_departure_pct`.

A movement is **on-time** when delay is at most `otp_on_time_tolerance_steps`. Map steps to minutes in your scenario design if you need an **OTP15**-style window (IATA/A4A convention: within 15 minutes of schedule).

## Configuration (JSON)

```json
{
  "schedule_mode": "published",
  "min_ground_time_steps": 9,
  "otp_on_time_tolerance_steps": 1
}
```

Use `"schedule_mode": "stochastic"` to restore the previous injection behavior.

## Implementation map

- `model/published_schedule.py` — build rotations at initialization  
- `agents/aircraft.py` — registration, MGT clock  
- `model/flight_scheduler.py` — activate legs by STA / STD / MGT  
- `metrics/otp.py` — post-run and step OTP reporters  

Next roadmap phase: **inbound delay**, **Ground Delay Program (GDP)**, and **airline irregular operations (IROPS)** cancellation logic.
