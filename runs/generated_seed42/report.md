# Mission report - Generated mission #42 (JSON example)

**Agent:** `bayesian`  
**Outcome:** reported - EVE LOCATED (visual contact)

## Recommended next step

> EVE is damaged at (28, 3). Stabilise her, avoid rubble on the way back, and carry her to the truck at (4, 8) for repairs.

## Inferred location & status

| | value |
|---|---|
| Most likely cell | `(28, 3)` |
| P(EVE within 1 cell) | 1.000 (HIGH) |
| 90% credible region | 1 cells |
| Posterior mean | `(28.0, 3.0)` |
| Status | **damaged** (1.00, HIGH) |
| Status posterior | active: 0.00, low_power: 0.00, damaged: 1.00 |

## Evidence

### Clues

| t | id | type | position | observation |
|---|---|---|---|---|
| 32 | clue4 | hover_tracks | `(24, 12)` | Fresh hover-scorch tracks pointing ~36 deg |
| 39 | clue2 | beacon_log | `(29, 8)` | Corrupted beacon log fragment: EVE x in [25, 30] |
| 44 | contact | visual_contact | `(28, 3)` | Visual contact, EVE looks damaged |

### Signal

- Scans: 6 (2 detections, 4 no-signal readings)
- Strongest: 35.7 at bearing 198 deg from `(23, 10)` (t=32)
- Learned fraction of spoofed readings: 19%
- 1 reading(s) flagged as probable spoof/decoy (live = at the time; hindsight = against the final belief):
  - t=32 at `(23, 10)`: 35.7 @ 198 deg (P(spoof) live 0.84, hindsight 1.00)

## Resources

- Time used: 44/400
- Battery consumed: 50.0 (remaining 30.0)
- Moves: 38, scans: 6, recharge steps: 0

## Strategy changes

- t=7 at `(9, 7)`: retarget `(12, 7)` -> `(11, 11)` - belief shifted 0.47 nats since plan
- t=32 at `(23, 10)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.35
- t=35 at `(26, 10)`: retarget `(26, 9)` -> `(28, 8)` - belief shifted 0.45 nats since plan
- t=39 at `(27, 8)`: retarget `(28, 8)` -> `(28, 5)` - new clue found
- t=42 at `(28, 6)`: retarget `(28, 5)` -> `(28, 3)` - belief shifted 0.60 nats since plan

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(28, 3)`, damaged
- Location error: 0.0 cells; status correct: True
- Clues found: 2/6
- Decoy readings received: 1, of which flagged: 1; genuine readings wrongly flagged: 0

## Final map

```
+------------------------------+
|..............##........~....?|
|..............##.........~#...|
|........?...............~.#...|
|.............?..~....###.~..E.|
|............###.~....###....W.|
|............###~...~.###....*.|
|...........~~~~~...~.#......*.|
|....******~~......~#.#.~..##*.|
|....S....*~~.......#~#~~..***b|
|.........***.......##..###*...|
|..~........*.......********...|
|...~...####*.......*..........|
|..##~..####*********....t.....|
|..##~..####..~~.##..###.......|
|..##...~~...~~....~~###.......|
|....####..####....~~###.......|
|....####..####......#D#..?....|
|.....###.#####................|
|.....###.#####..............C.|
|.........####..#..............|
+------------------------------+
Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)
        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)
        ? clue missed  D decoy transmitter
```
