# Mission report - Decoy gauntlet

**Agent:** `bayesian-naive`  
**Outcome:** reported - EVE not visually confirmed

## Recommended next step

> Recharge at (2, 6), then travel directly to (5, 13) (P(EVE within 1 cell) = 0.85) and scan on arrival.

## Inferred location & status

| | value |
|---|---|
| Most likely cell | `(5, 13)` |
| P(EVE within 1 cell) | 0.848 (HIGH) |
| 90% credible region | 6 cells |
| Posterior mean | `(4.94, 12.58)` |
| Status | **damaged** (1.00, HIGH) |
| Status posterior | active: 0.00, low_power: 0.00, damaged: 1.00 |

## Evidence

### Clues

_No physical clues found._

### Signal

- Scans: 60 (45 detections, 15 no-signal readings)
- Strongest: 80.6 at bearing 13 deg from `(0, 18)` (t=88)
- Learned fraction of spoofed readings: 0%

## Resources

- Time used: 391/400
- Battery consumed: 426.0 (remaining 100.0)
- Moves: 306, scans: 60, recharge steps: 25

## Strategy changes

- t=10 at `(3, 3)`: retarget `(15, 4)` -> `(8, 12)` - belief shifted 3.34 nats since plan
- t=21 at `(3, 11)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.28
- t=21 at `(3, 11)`: retarget `(8, 12)` -> `(3, 16)` - belief shifted 1.84 nats since plan
- t=27 at `(3, 16)`: **PURSUE -> EXPLORE** - P(EVE near target)=0.21
- t=28 at `(2, 16)`: retarget `(0, 16)` -> `(5, 18)` - planned route blocked by newly seen wall
- t=32 at `(4, 18)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.28
- t=32 at `(4, 18)`: retarget `(5, 18)` -> `(6, 17)` - belief shifted 0.49 nats since plan
- t=39 at `(8, 18)`: retarget `(9, 18)` -> `(11, 19)` - belief shifted 0.59 nats since plan
- t=44 at `(11, 19)`: **PURSUE -> RECHARGE** - Battery 30.0 only covers return trip (22.0) + reserve 6.0
- t=71 at `(2, 6)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=71 at `(2, 6)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.41
- t=76 at `(2, 10)`: retarget `(9, 15)` -> `(0, 18)` - belief shifted 0.58 nats since plan
- t=99 at `(1, 13)`: **PURSUE -> EXPLORE** - P(EVE near target)=0.11
- t=99 at `(1, 13)`: retarget `(2, 11)` -> `(5, 12)` - belief shifted 2.01 nats since plan
- t=105 at `(5, 12)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.32
- t=125 at `(1, 11)`: retarget `(0, 9)` -> `(0, 8)` - belief shifted 0.53 nats since plan
- t=128 at `(0, 9)`: **PURSUE -> EXPLORE** - P(EVE near target)=0.19
- t=128 at `(0, 9)`: retarget `(0, 8)` -> `(6, 10)` - belief shifted 0.49 nats since plan
- t=134 at `(4, 10)`: **EXPLORE -> RECHARGE** - Best target (4,17) (utility 0.281) is out of range on current battery 24; recharging first
- t=145 at `(2, 6)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=145 at `(2, 6)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.71
- t=155 at `(2, 16)`: retarget `(3, 18)` -> `(3, 17)` - belief shifted 0.58 nats since plan
- t=160 at `(1, 17)`: retarget `(1, 18)` -> `(0, 18)` - belief shifted 1.18 nats since plan
- t=161 at `(1, 18)`: retarget `(0, 18)` -> `(6, 15)` - belief shifted 0.52 nats since plan
- t=167 at `(4, 15)`: retarget `(6, 15)` -> `(6, 16)` - belief shifted 0.69 nats since plan
- t=169 at `(5, 16)`: retarget `(6, 16)` -> `(4, 18)` - belief shifted 0.48 nats since plan
- t=186 at `(5, 14)`: retarget `(6, 14)` -> `(6, 17)` - belief shifted 2.51 nats since plan
- t=189 at `(5, 17)`: retarget `(6, 17)` -> `(6, 18)` - belief shifted 0.54 nats since plan
- t=196 at `(6, 14)`: retarget `(7, 13)` -> `(8, 12)` - belief shifted 0.56 nats since plan
- t=199 at `(6, 12)`: retarget `(8, 12)` -> `(2, 12)` - belief shifted 1.76 nats since plan
- t=202 at `(3, 12)`: retarget `(2, 12)` -> `(1, 11)` - belief shifted 0.62 nats since plan
- t=203 at `(2, 12)`: retarget `(1, 11)` -> `(1, 10)` - belief shifted 0.68 nats since plan
- t=205 at `(1, 11)`: retarget `(1, 10)` -> `(2, 9)` - belief shifted 0.62 nats since plan
- t=212 at `(3, 10)`: retarget `(4, 10)` -> `(2, 15)` - belief shifted 0.71 nats since plan
- t=219 at `(2, 15)`: **PURSUE -> RECHARGE** - Battery 17.0 only covers return trip (9.0) + reserve 6.0
- t=233 at `(2, 6)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=234 at `(2, 6)`: **EXPLORE -> PURSUE** - P(EVE near target)=0.86
- t=243 at `(1, 14)`: retarget `(1, 16)` -> `(2, 16)` - belief shifted 0.93 nats since plan
- t=245 at `(1, 15)`: retarget `(2, 16)` -> `(5, 10)` - belief shifted 1.24 nats since plan
- t=254 at `(4, 10)`: retarget `(5, 10)` -> `(2, 17)` - belief shifted 1.40 nats since plan
- t=263 at `(2, 16)`: retarget `(2, 17)` -> `(1, 18)` - belief shifted 1.36 nats since plan
- t=275 at `(3, 13)`: retarget `(4, 13)` -> `(7, 10)` - belief shifted 0.83 nats since plan
- t=279 at `(5, 11)`: retarget `(7, 10)` -> `(4, 18)` - belief shifted 0.51 nats since plan
- t=286 at `(4, 16)`: retarget `(4, 18)` -> `(3, 17)` - belief shifted 1.28 nats since plan
- t=298 at `(1, 18)`: **PURSUE -> RECHARGE** - Battery 21.0 only covers return trip (13.0) + reserve 6.0
- t=316 at `(2, 6)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search
- t=316 at `(2, 6)`: **EXPLORE -> PURSUE** - P(EVE near target)=1.00
- t=356 at `(2, 17)`: retarget `(3, 17)` -> `(1, 18)` - belief shifted 0.68 nats since plan
- t=370 at `(2, 12)`: retarget `(1, 12)` -> `(1, 11)` - belief shifted 1.32 nats since plan
- t=377 at `(1, 14)`: **PURSUE -> RECHARGE** - Best target (5,13) (utility 0.350) is out of range on current battery 21; recharging first
- t=391 at `(2, 6)`: **RECHARGE -> EXPLORE** - Battery restored to 100; resuming search

## Ground-truth check (simulation only - hidden from the agent)

- True EVE: `(26, 7)`, low_power
- Location error: 21.84 cells; status correct: False
- Clues found: 0/6
- Decoy readings received: 45, of which flagged: 0; genuine readings wrongly flagged: 0

## Final map

```
+------------------------------+
|....................###.......|
|.............?...~~.###.......|
|................~~~....#####..|
|..**.######..........~.#####..|
|.***.######.......####?#####..|
|.**#~~~~.........?####~.##....|
|.*W#####~.........#####......?|
|.**#...~~..........####?..E...|
|.**.~~................###.....|
|****~###........~?....###.....|
|*****.~.........~~....###.....|
|******..........~~.......#....|
|#*D****.........~........###..|
|#****e*........~..............|
|#******...................~.~~|
|.******##............##....~~~|
|#******............~~##.....~~|
|#******...####......~~........|
|D********.####.......~........|
|..**********.....####........C|
+------------------------------+
Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)
        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)
        ? clue missed  D decoy transmitter
```
