# Mission report - Decoy gauntlet

**Agent:** `team of 2 x bayesian`  
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
| 21 | clue4 | beacon_log | `(17, 9)` | Corrupted beacon log fragment: EVE x in [26, 31] |
| 68 | clue2 | power_cell | `(29, 6)` | Discarded EVE power cell; drag marks lead within 5 cells |
| 69 | contact | visual_contact | `(26, 7)` | Visual contact, EVE looks low_power |

### Signal

- Scans: 12 (8 detections, 4 no-signal readings)
- Strongest: 38.7 at bearing 240 deg from `(6, 8)` (t=9)
- Learned fraction of spoofed readings: 36%
- Suspected decoy transmitter near `(1, 12)` (P within 1 cell = 0.91)
- 6 reading(s) flagged as probable spoof/decoy (live = at the time; hindsight = against the final belief):
  - t=9 at `(6, 8)`: 38.7 @ 240 deg (P(spoof) live 0.95, hindsight 1.00)
  - t=10 at `(4, 10)`: 31.2 @ 198 deg (P(spoof) live 0.97, hindsight 1.00)
  - t=19 at `(7, 10)`: 26.5 @ 105 deg (P(spoof) live 0.63, hindsight 1.00)
  - t=21 at `(16, 8)`: 16.8 @ 254 deg (P(spoof) live 0.78, hindsight 0.99)
  - t=28 at `(20, 10)`: 13.1 @ 276 deg (P(spoof) live 0.80, hindsight 0.99)
  - t=45 at `(5, 18)`: 37.1 @ 328 deg (P(spoof) live 1.00, hindsight 1.00)

## Resources

- Time used: 69/400
- Battery consumed: 147.0 (remaining 173.0)
- Moves: 111, scans: 12, recharge steps: 9

| robot | moves | scans | recharge steps | battery used | battery left |
|---|---|---|---|---|---|
| WALL-E | 58 | 5 | 5 | 70.0 | 96.0 |
| M-O | 53 | 7 | 4 | 77.0 | 77.0 |

## Strategy changes

- **WALL-E** t=16 at `(9, 10)`: retarget `(11, 10)` -> `(2, 14)` - belief shifted 0.50 nats since plan
- **M-O** t=16 at `(12, 8)`: retarget `(22, 8)` -> `(16, 8)` - belief shifted 0.71 nats since plan
- **WALL-E** t=21 at `(6, 11)`: retarget `(2, 14)` -> `(7, 15)` - new clue found
- **WALL-E** t=23 at `(6, 13)`: retarget `(7, 15)` -> `(2, 13)` - planned route blocked by newly seen wall
- **WALL-E** t=35 at `(7, 11)`: retarget `(12, 11)` -> `(5, 18)` - belief shifted 1.27 nats since plan
- **M-O** t=35 at `(23, 13)`: **EXPLORE -> RECHARGE** - Best target (28,7) (utility 0.201) is out of range on current battery 38; recharging first
- **WALL-E** t=45 at `(5, 18)`: **EXPLORE -> RECHARGE** - Best target (12,19) (utility 0.053) is out of range on current battery 29; recharging first
- **M-O** t=51 at `(29, 19)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- **M-O** t=51 at `(29, 19)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.37
- **WALL-E** t=65 at `(2, 6)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- **WALL-E** t=68 at `(1, 4)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.84
- **WALL-E** t=68 at `(1, 4)`: retarget `(1, 0)` -> `(26, 6)` - new clue found

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(26, 7)`, low_power
- Location error: 0.0 cells; status correct: True
- Clues found: 2/6
- Decoy readings received: 6, of which flagged: 6; genuine readings wrongly flagged: 0

## Final map

```
+------------------------------+
|....................###.......|
|.............?...~~.###.......|
|................~~~....#####..|
|.....######..........~.#####..|
|.*W..######.......####?#####..|
|.*.#~~~~.........?####~.##....|
|.*S#####~.........#####......p|
|.**#...~~..........####?..E...|
|.********************.###..M*.|
|.**.~###........~b..*.###...*.|
|.*********......~~..**###...*.|
|..******........~~...***.#..*.|
|#.D..**.........~......*.###*.|
|#.*****........~.......*....*.|
|#.*..*.................*..~.*~|
|..*..*.##............##*...~*~|
|#.*..*.............~~##*....*~|
|#.*..*....####......~~.*....*.|
|D.****....####.......~.*....*.|
|.................####..******C|
+------------------------------+
Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)
        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)
        ? clue missed  D decoy transmitter
```
