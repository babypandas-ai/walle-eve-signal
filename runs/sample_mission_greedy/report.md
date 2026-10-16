# Mission report - Downtown after the dust storm

**Agent:** `greedy`  
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
| 184 | log-1 | beacon_log | `(12, 2)` | Corrupted beacon log fragment: EVE y in [1, 6] |
| 218 | tracks-1 | hover_tracks | `(16, 9)` | Fresh hover-scorch tracks pointing ~69 deg |
| 226 | cell-1 | power_cell | `(23, 9)` | Discarded EVE power cell; drag marks lead within 9 cells |
| 231 | plant | plant | `(25, 6)` | A seedling in an old boot! EVE must be within 4 cells |
| 252 | contact | visual_contact | `(27, 5)` | Visual contact, EVE looks low_power |

### Signal

- Scans: 55 (9 detections, 46 no-signal readings)
- Strongest: 35.1 at bearing 13 deg from `(26, 7)` (t=251)
- Learned fraction of spoofed readings: 14%
- Suspected decoy transmitter near `(27, 19)` (P within 1 cell = 0.33)
- 2 reading(s) flagged as probable spoof/decoy (live = at the time; hindsight = against the final belief):
  - t=196 at `(17, 6)`: 15.2 @ 134 deg (P(spoof) live 0.11, hindsight 0.87)
  - t=231 at `(23, 7)`: 23.8 @ 171 deg (P(spoof) live 0.98, hindsight 1.00)

## Resources

- Time used: 252/400
- Battery consumed: 294.0 (remaining 55.0)
- Moves: 180, scans: 55, recharge steps: 15

## Strategy changes

- t=45 at `(1, 6)`: **EXPLORE -> RECHARGE** - Battery 13.0 only covers return trip (5.0) + reserve 6
- t=55 at `(1, 1)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=121 at `(9, 0)`: **EXPLORE -> RECHARGE** - Battery 17.0 only covers return trip (9.0) + reserve 6
- t=135 at `(1, 1)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=204 at `(22, 7)`: **EXPLORE -> RECHARGE** - Battery 13.0 only covers return trip (8.0) + reserve 6
- t=217 at `(17, 10)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(27, 5)`, low_power
- Location error: 0.0 cells; status correct: True
- Clues found: 4/5
- Decoy readings received: 2, of which flagged: 2; genuine readings wrongly flagged: 0

## Final map

```
+--------------------------------+
|**********......................|
|*S******###.......~~~...........|
|***....*###.b.....~~~?...####...|
|**##...*###..............####...|
|**##...**********###.....####...|
|**.......~~~....*###.......E....|
|**..#....~~~....***...~~~gW.....|
|**..#.........###*******~.*.##..|
|**..#.........###*...******.##..|
|**......###.....t*.....p#.......|
|**~~....###......C******#.......|
|**~~....###.............#....~~.|
|**.............###...........~~.|
|**....###......###..~~~.........|
|**....###...........~~~....###..|
|.*...........##............###..|
|.*.~~~.......##..........D......|
|.*.~~~..............###.........|
|.*..................###.......C.|
|**..............................|
+--------------------------------+
Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)
        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)
        ? clue missed  D decoy transmitter
```
