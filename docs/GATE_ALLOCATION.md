# Phase C: preferential gates, common-use, remote stands, gate class

Gate assignment follows hybrid **preferential / common-use** practice used at many commercial airports.

## Terminology

| Term | Meaning in this model |
|------|------------------------|
| **Preferential gate** | Contact gate with first rights for a specific airline (`gates_per_airline`) |
| **Common-use gate** | Contact gate available to any airline when preferential stands are full (remainder of `n_gates`) |
| **Remote stand** | Hardstand away from the terminal; requires **bus transfer** time |
| **Gate class** | **Narrowbody** or **widebody** capability |
| **Aircraft type** | Narrowbody or widebody (widebody share configurable) |
| **Gate buffer** | Minimum steps after release before the stand may be reassigned |

## Compatibility

- A **widebody** gate accepts narrowbody and widebody aircraft.
- A **narrowbody** gate accepts narrowbody only.

## Assignment order (`GateAllocator`)

1. Preferential gate for the operating airline (compatible class)  
2. Common-use contact gate  
3. Remote stand  
4. Otherwise **gate hold** (flight waits and retries next step)

## Remote stand time penalty

When assigned a remote stand:

- Boarding / disembark occupancy += `remote_bus_transfer_steps`
- Taxi-out += `remote_bus_transfer_steps` (bus back to terminal / apron flow proxy)

## Default inventory (`n_gates=100`)

- Preferential: `(55, 12, 13)` = 80  
- Common-use: 20  
- Remote stands: 10 (`n_remote_stands`)  
- ~25% of stands are widebody class (`widebody_gate_share`)

## Configuration

```json
{
  "gates_per_airline": [55, 12, 13],
  "n_gates": 100,
  "n_remote_stands": 10,
  "remote_bus_transfer_steps": 2,
  "widebody_share": 0.15,
  "widebody_gate_share": 0.25,
  "gate_buffer_steps": 1
}
```

If `sum(gates_per_airline) == n_gates`, there are **no** common-use contact gates (exclusive preferential only). Remote stands remain available if `n_remote_stands > 0`.

## Metrics (time series)

| Column | Description |
|--------|-------------|
| `preferential_assignments` | Preferential assignments this step |
| `common_use_assignments` | Common-use assignments this step |
| `remote_stand_assignments` | Remote stand assignments this step |
| `gate_holds` | Failed assignment attempts this step (wait) |

## Implementation map

| File | Role |
|------|------|
| `agents/gate_class.py` | Aircraft type, gate class, use type, compatibility |
| `agents/gate.py` | Gate inventory (preferential / common-use / remote) |
| `agents/gate_allocator.py` | Assignment policy + counters |
| `agents/flight.py` | Uses allocator; remote bus transfer on occupancy / taxi-out |

## Not yet modeled (later phases)

- Tow-off / tow-to-remote mid-turnaround  
- IROPS gate priority by connection load  
- International vs domestic pier constraints  
- Full schedule-based gate planning (Gantt) before day-of-ops  

Next roadmap phase: **connecting passengers (MCT)** and terminal level of service.
