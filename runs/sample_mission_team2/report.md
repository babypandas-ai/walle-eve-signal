# Mission report - Downtown after the dust storm

**Agent:** `team of 2 x bayesian`  
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
| 14 | log-1 | beacon_log | `(12, 2)` | Corrupted beacon log fragment: EVE x in [22, 27] |
| 28 | tracks-1 | hover_tracks | `(16, 9)` | Fresh hover-scorch tracks pointing ~55 deg |
| 52 | plant | plant | `(25, 6)` | A seedling in an old boot! EVE must be within 4 cells |
| 56 | contact | visual_contact | `(27, 5)` | Visual contact, EVE looks low_power |

### Signal

- Scans: 12 (6 detections, 6 no-signal readings)
- Strongest: 40.0 at bearing 80 deg from `(25, 5)` (t=55)
- Learned fraction of spoofed readings: 26%
- Suspected decoy transmitter near `(26, 19)` (P within 1 cell = 0.51)
- 3 reading(s) flagged as probable spoof/decoy (live = at the time; hindsight = against the final belief):
  - t=24 at `(15, 5)`: 13.5 @ 13 deg (P(spoof) live 0.84, hindsight 0.94)
  - t=38 at `(17, 9)`: 21.3 @ 142 deg (P(spoof) live 0.99, hindsight 1.00)
  - t=45 at `(20, 6)`: 22.6 @ 154 deg (P(spoof) live 1.00, hindsight 1.00)

## Resources

- Time used: 56/400
- Battery consumed: 115.0 (remaining 161.0)
- Moves: 91, scans: 12, recharge steps: 8

| robot | moves | scans | recharge steps | battery used | battery left |
|---|---|---|---|---|---|
| WALL-E | 45 | 7 | 4 | 59.0 | 76.0 |
| M-O | 46 | 5 | 4 | 56.0 | 85.0 |

## Strategy changes

- **WALL-E** t=7 at `(5, 1)`: retarget `(12, 2)` -> `(10, 10)` - belief shifted 0.67 nats since plan
- **M-O** t=7 at `(6, 0)`: retarget `(21, 1)` -> `(21, 0)` - belief shifted 0.67 nats since plan
- **WALL-E** t=14 at `(7, 6)`: retarget `(10, 10)` -> `(8, 5)` - new clue found
- **M-O** t=14 at `(12, 0)`: retarget `(21, 0)` -> `(15, 5)` - new clue found
- **M-O** t=27 at `(12, 5)`: **EXPLORE -> RECHARGE** - Best target (26,1) (utility 0.131) is out of range on current battery 39; recharging first
- **WALL-E** t=28 at `(14, 9)`: **EXPLORE -> RECHARGE** - Best target (25,2) (utility 0.129) is out of range on current battery 39; recharging first
- **WALL-E** t=36 at `(17, 10)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- **M-O** t=41 at `(17, 10)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- **WALL-E** t=45 at `(20, 6)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.36
- **M-O** t=45 at `(18, 12)`: retarget `(22, 12)` -> `(26, 7)` - belief shifted 0.50 nats since plan
- **M-O** t=51 at `(20, 8)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.82
- **M-O** t=51 at `(20, 8)`: retarget `(26, 7)` -> `(26, 6)` - new clue found
- **WALL-E** t=52 at `(23, 5)`: retarget `(26, 4)` -> `(25, 5)` - new clue found
- **M-O** t=54 at `(23, 8)`: retarget `(26, 6)` -> `(27, 6)` - belief shifted 0.50 nats since plan

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(27, 5)`, low_power
- Location error: 0.0 cells; status correct: True
- Clues found: 3/5
- Decoy readings received: 3, of which flagged: 3; genuine readings wrongly flagged: 0

## Final map

```
+--------------------------------+
|......*******...................|
|.S*****.###.*.....~~~...........|
|.*****..###.b**...~~~?...####...|
|..##.*..###...*..........####...|
|..##.***......*..###****.####...|
|.......**~~~****.###*..***WE....|
|....#..**~~~*....****.~~~g......|
|....#...*...*.###*....~~~...##..|
|....#...*****.###*******M...##..|
|........###****.t**....?#.......|
|..~~....###.*****C*.....#.......|
|..~~....###......**.....#....~~.|
|...............###*..........~~.|
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
