# Mission report - Downtown after the dust storm

**Agent:** `bayesian`  
**Outcome:** reported - EVE LOCATED (visual contact)

## Recommended next step

> EVE is in low-power standby at (27, 5). Carry her to the nearest charger (17, 10) (~11 cells) and recharge her before attempting to wake her.

## Inferred location & status

| | value |
|---|---|
| Most likely cell | `(27, 5)` |
| P(EVE within 1 cell) | 1.000 (HIGH) |
| 90% credible region | 1 cells |
| Posterior mean | `(27.0, 5.0)` |
| Status | **low_power** (1.00, HIGH) |
| Status posterior | active: 0.00, low_power: 1.00, damaged: 0.00 |

## Evidence

### Clues

| t | id | type | position | observation |
|---|---|---|---|---|
| 26 | log-1 | beacon_log | `(12, 2)` | Corrupted beacon log fragment: EVE y in [3, 8] |
| 63 | plant | plant | `(25, 6)` | A seedling in an old boot! EVE must be within 4 cells |
| 63 | tracks-2 | hover_tracks | `(21, 2)` | Fresh hover-scorch tracks pointing ~118 deg |
| 67 | contact | visual_contact | `(27, 5)` | Visual contact, EVE looks low_power |

### Signal

- Scans: 7 (4 detections, 3 no-signal readings)
- Strongest: 17.4 at bearing 13 deg from `(18, 6)` (t=33)
- Learned fraction of spoofed readings: 29%
- Suspected decoy transmitter near `(27, 19)` (P within 1 cell = 0.47)
- 3 reading(s) flagged as probable spoof/decoy (live = at the time; hindsight = against the final belief):
  - t=26 at `(14, 4)`: 12.7 @ 144 deg (P(spoof) live 0.94, hindsight 1.00)
  - t=33 at `(18, 6)`: 17.4 @ 13 deg (P(spoof) live 0.84, hindsight 0.94)
  - t=63 at `(23, 4)`: 15.8 @ 170 deg (P(spoof) live 0.98, hindsight 1.00)

## Resources

- Time used: 67/400
- Battery consumed: 69.0 (remaining 82.0)
- Moves: 55, scans: 7, recharge steps: 5

## Strategy changes

- t=8 at `(6, 1)`: retarget `(12, 2)` -> `(8, 6)` - belief shifted 0.55 nats since plan
- t=26 at `(14, 4)`: retarget `(16, 4)` -> `(20, 5)` - new clue found
- t=37 at `(20, 5)`: **EXPLORE -> RECHARGE** - Best target (28,4) (utility 0.234) is out of range on current battery 27; recharging first
- t=50 at `(17, 10)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=50 at `(17, 10)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.40
- t=64 at `(23, 5)`: retarget `(27, 4)` -> `(26, 4)` - new clue found
- t=65 at `(24, 5)`: retarget `(26, 4)` -> `(27, 5)` - planned route blocked by newly seen wall

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(27, 5)`, low_power
- Location error: 0.0 cells; status correct: True
- Clues found: 3/5
- Decoy readings received: 3, of which flagged: 3; genuine readings wrongly flagged: 0

## Final map

```
+--------------------------------+
|................................|
|.S....*.###.......~~~...........|
|.******.###.b.....~~~t...####...|
|..##..*.###..............####...|
|..##..*********..###****.####...|
|........*~~~..**.###*..***WE....|
|....#...*~~~...******.~~~g......|
|....#.........###*....~~~...##..|
|....#.........###*..........##..|
|........###.....?*.....?#.......|
|..~~....###......C......#.......|
|..~~....###.............#....~~.|
|...............###...........~~.|
|......###......###..~~~.........|
|......###...........~~~....###..|
|.............##............###..|
|...~~~.......##..........D......|
|...~~~..............###.........|
|....................###.......C.|
|................................|
+--------------------------------+
Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)
        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)
        ? clue missed  D decoy transmitter
```
