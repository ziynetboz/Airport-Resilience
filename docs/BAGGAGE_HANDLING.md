# Phase E: baggage handling (transfer, make-up, claim)

## Flows (industry terms)

| Bag type | Path |
|----------|------|
| **Local originating** | Check-in → **make-up** → loaded on departure |
| **Transfer** | Inbound unload → **transfer** → make-up → loaded on outbound |
| **Local terminating** | Unload → **baggage claim** |

Bags are modeled as **batches** (counts on the same itinerary), not one agent per bag.

## Timing parameters

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `bags_per_passenger` | 1.0 | Bags created per passenger |
| `bag_unload_steps` | 2 | Unload from inbound aircraft |
| `bag_transfer_steps` | 3 | Transfer sort / connect time |
| `bag_make_up_steps` | 2 | Departure make-up |
| `bag_claim_steps` | 2 | Arrival claim |

## Mishandled bags

A transfer (or late originating) bag is **mishandled** if the outbound has already pushed (taxi-out / runway queue / completed) before the bag reaches **loaded**.

## Departure hold (bag-induced delay)

When `bag_hold_departure` is true, a departure at gate does not push back until all of its bags are **loaded** or already **mishandled** (left behind). This creates bag-driven delay on the critical path.

## Configuration

```json
{
  "baggage_enabled": true,
  "bags_per_passenger": 1.0,
  "bag_unload_steps": 2,
  "bag_transfer_steps": 3,
  "bag_make_up_steps": 2,
  "bag_claim_steps": 2,
  "bag_hold_departure": true
}
```

## Metrics

| Column | Description |
|--------|-------------|
| `bags_in_process` | Bags not yet loaded / claimed / mishandled |
| `bags_loaded` | Bags loaded this step |
| `bags_claimed` | Bags claimed this step |
| `mishandled_bags` | Mishandled this step |
| `bag_holds` | Departures held for bags this step |

## Implementation map

| File | Role |
|------|------|
| `agents/bag_types.py` | Bag type and state enums |
| `agents/baggage.py` | `BagBatch` process logic |
| `agents/baggage_handling.py` | System, readiness check, creation |
| `agents/flight.py` | Pushback hold until bags ready |

## Step order

Baggage handling runs **before** flight airside progress so make-up completion can release a bag hold in the same step cycle when appropriate.

Roadmap Phase E complete. Optional later: carousel capacity, screening surge, tow-linked bag moves.
