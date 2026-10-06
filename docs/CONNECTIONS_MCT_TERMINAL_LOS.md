# Phase D: connecting passengers (MCT) and terminal Level of Service (LoS)

## Passenger types

| Type | Industry meaning | Model behavior |
|------|------------------|----------------|
| **Originating** | Local departure | Starts in terminal; exits when outbound completes |
| **Terminating** | Local arrival | Enters terminal after inbound on-block; exits next step |
| **Connecting** | Transfer passenger | Inbound then outbound; must satisfy **MCT** |

## Minimum Connection Time (MCT)

- Config: `mct_steps` (default 6)
- Connecting share of inbound passengers: `connecting_passenger_share` (default 0.35)
- Connections prefer the **same airline**; otherwise any outbound with  
  `STD >= STA + MCT`
- **Misconnect**: available connection time (ATD − ATA/on-block) &lt; effective MCT, or the outbound leaves before the passenger is ready

When the terminal is **overcrowded**, effective MCT becomes  
`mct_steps + los_overcrowd_mct_penalty_steps` (congestion slows connections).

## Terminal Level of Service (LoS)

Occupancy = passengers in `IN_TERMINAL` or `OUTBOUND`.  
Ratio = occupancy / `terminal_capacity`.

| Ratio | LoS |
|-------|-----|
| ≤ 0.40 | A |
| ≤ 0.60 | B |
| ≤ 0.80 | C |
| ≤ 1.00 | D |
| ≤ 1.20 | E |
| &gt; 1.20 | F |

- `terminal_overcrowded` when occupancy &gt; `terminal_capacity`
- Optional hard deferral of terminal entry: `terminal_capacity_enforced: true`

## Configuration

```json
{
  "connecting_passenger_share": 0.35,
  "mct_steps": 6,
  "terminal_capacity": 5000,
  "terminal_los_enabled": true,
  "terminal_capacity_enforced": false,
  "los_overcrowd_mct_penalty_steps": 2
}
```

## Metrics

| Column | Description |
|--------|-------------|
| `travelers_misconnected` | Cumulative misconnect count |
| `connecting_in_terminal` | Connecting passengers still airside/terminal |
| `terminal_occupancy_ratio` | Occupancy / capacity |
| `terminal_los` | LoS letter A–F |
| `terminal_overcrowded` | 0/1 |

## Implementation map

| File | Role |
|------|------|
| `agents/passenger_type.py` | Originating / terminating / connecting |
| `agents/traveler.py` | MCT check, misconnect state |
| `agents/terminal_los.py` | Occupancy, LoS bands, MCT penalty |
| `model/connections.py` | Link connecting passengers to outbounds |

Next (Phase E): **baggage handling** (transfer bags, make-up, claim).
