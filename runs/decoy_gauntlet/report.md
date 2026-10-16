# Mission report - Decoy gauntlet

**Agent:** `bayesian`  
**Outcome:** reported - EVE LOCATED (visual contact)

## Recommended next step

> EVE is in low-power standby at (26, 7). Carry her to the nearest charger (29, 19) (~12 cells) and recharge her before attempting to wake her.

## Inferred location & status

| | value |
|---|---|
| Most likely cell | `(26, 7)` |
| P(EVE within 1 cell) | 1.000 (HIGH) |
| 90% credible region | 1 cells |
| Posterior mean | `(26.0, 7.0)` |
| Status | **low_power** (1.00, HIGH) |
| Status posterior | active: 0.00, low_power: 1.00, damaged: 0.00 |

## Evidence

### Clues

| t | id | type | position | observation |
|---|---|---|---|---|
| 28 | clue4 | beacon_log | `(17, 9)` | Corrupted beacon log fragment: EVE y in [7, 12] |
| 77 | contact | visual_contact | `(26, 7)` | Visual contact, EVE looks low_power |

### Signal

- Scans: 9 (7 detections, 2 no-signal readings)
- Strongest: 50.6 at bearing 240 deg from `(4, 10)` (t=10)
- Learned fraction of spoofed readings: 33%
- Suspected decoy transmitter near `(2, 18)` (P within 1 cell = 0.46)
- 4 reading(s) flagged as probable spoof/decoy (live = at the time; hindsight = against the final belief):
  - t=10 at `(4, 10)`: 50.6 @ 240 deg (P(spoof) live 0.95, hindsight 1.00)
  - t=18 at `(9, 9)`: 24.3 @ 216 deg (P(spoof) live 0.98, hindsight 1.00)
  - t=35 at `(20, 11)`: 16.0 @ 254 deg (P(spoof) live 0.97, hindsight 0.99)
  - t=67 at `(27, 14)`: 8.3 @ 275 deg (P(spoof) live 1.00, hindsight 1.00)

## Resources

- Time used: 77/400
- Battery consumed: 84.0 (remaining 78.0)
- Moves: 60, scans: 9, recharge steps: 5

## Strategy changes

- t=28 at `(16, 9)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.25
- t=40 at `(24, 11)`: **PURSUE -> RECHARGE** - Best target (27,8) (utility 0.256) is out of range on current battery 31; recharging first
- t=58 at `(29, 19)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=58 at `(29, 19)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.69
- t=75 at `(26, 10)`: retarget `(26, 8)` -> `(26, 7)` - belief shifted 0.66 nats since plan

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(26, 7)`, low_power
- Location error: 0.0 cells; status correct: True
- Clues found: 1/6
- Decoy readings received: 5, of which flagged: 4; genuine readings wrongly flagged: 0

## Final map

```
+------------------------------+
|....................###.......|
|.............?...~~.###.......|
|................~~~....#####..|
|.....######..........~.#####..|
|.....######.......####?#####..|
|...#~~~~.........?####~.##....|
|.*S#####~.........#####......?|
|.*.#...~~..........####?..E...|
|.*..~~................###.W...|
|.***~###*********b*...###.*...|
|...******.......~~*...###.*...|
|................~~*******#***.|
|#.D.............~.......*###*.|
|#..............~........*..**.|
|#.......................*.~*~~|
|.......##............##.*..*~~|
|#..................~~##.*..*~~|
|#.........####......~~..*..*..|
|D.........####.......~..*..*..|
|.................####...*****C|
+------------------------------+
Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)
        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)
        ? clue missed  D decoy transmitter
```
