# Mission report - Procedural wasteland

**Agent:** `bayesian`  
**Outcome:** reported - EVE LOCATED (visual contact)

## Recommended next step

> EVE is damaged at (33, 12). Stabilise her, avoid rubble on the way back, and carry her to the truck at (2, 8) for repairs.

## Inferred location & status

| | value |
|---|---|
| Most likely cell | `(33, 12)` |
| P(EVE within 1 cell) | 1.000 (HIGH) |
| 90% credible region | 1 cells |
| Posterior mean | `(33.0, 12.0)` |
| Status | **damaged** (1.00, HIGH) |
| Status posterior | active: 0.00, low_power: 0.00, damaged: 1.00 |

## Evidence

### Clues

| t | id | type | position | observation |
|---|---|---|---|---|
| 92 | clue3 | hover_tracks | `(29, 5)` | Fresh hover-scorch tracks pointing ~146 deg |
| 102 | clue2 | debris | `(29, 10)` | EVE armour fragment; scatter pattern says source within 6 cells |
| 102 | clue5 | plant | `(32, 9)` | A seedling in an old boot! EVE must be within 5 cells |
| 105 | contact | visual_contact | `(33, 12)` | Visual contact, EVE looks damaged |

### Signal

- Scans: 9 (4 detections, 5 no-signal readings)
- Strongest: 22.1 at bearing 165 deg from `(31, 9)` (t=102)
- Learned fraction of spoofed readings: 18%
- 1 reading(s) flagged as probable spoof/decoy (live = at the time; hindsight = against the final belief):
  - t=19 at `(14, 4)`: 9.0 @ 222 deg (P(spoof) live 0.90, hindsight 1.00)

## Resources

- Time used: 105/400
- Battery consumed: 113.0 (remaining 37.0)
- Moves: 87, scans: 9, recharge steps: 5

## Strategy changes

- t=10 at `(9, 6)`: retarget `(11, 6)` -> `(14, 4)` - planned route blocked by newly seen wall
- t=25 at `(17, 2)`: **EXPLORE -> RECHARGE** - Best target (25,1) (utility 0.167) is out of range on current battery 36; recharging first
- t=51 at `(2, 8)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=92 at `(28, 5)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.39
- t=92 at `(28, 5)`: retarget `(29, 5)` -> `(32, 9)` - new clue found
- t=102 at `(31, 9)`: retarget `(32, 9)` -> `(32, 13)` - new clue found

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(33, 12)`, damaged
- Location error: 0.0 cells; status correct: True
- Clues found: 3/5
- Decoy readings received: 1, of which flagged: 1; genuine readings wrongly flagged: 0

## Final map

```
+----------------------------------+
|..#.....~~~~.~..............~~~~..|
|.....##..~~~~..............~~..~..|
|..#####....~**************........|
|..##########*.*...~~~~~~.***..~...|
|..####..####***....~~##~~~~*..~~~.|
|...#*********####...##...~~**t####|
|...#*...**.######.#.##..~...*.####|
|..***...*..######.#.##.~....***...|
|..S******........?#~~.........*...|
|...........##......~~.....#...**g.|
|......###..##.......~........d~**.|
|...........##..............#...~W.|
|...............####.......##..~..E|
|........................~~##......|
|...............#.........~~.......|
|...............#.....#..........?.|
|.....................#............|
|..####...............#.......##...|
|..##D#............................|
|......................####........|
|................##...............C|
|................##................|
+----------------------------------+
Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)
        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)
        ? clue missed  D decoy transmitter
```
