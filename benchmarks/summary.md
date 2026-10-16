# Benchmark results

25 random missions per tier (seeds 1000..1024); every agent sees identical missions.

| tier | agent | success | median loc. error | status acc. | time when found | battery used | stranded | clues |
|---|---|---|---|---|---|---|---|---|
| standard | bayesian | 100% | 0.0 | 100% | 63.2 | 70.0 | 0% | 1.44 |
| standard | bayesian@2 | 100% | 0.0 | 100% | 51.2 | 111.0 | 0% | 1.6 |
| standard | bayesian-naive | 100% | 0.0 | 100% | 63.7 | 70.2 | 0% | 1.52 |
| standard | greedy | 72% | 0.0 | 100% | 122.3 | 233.9 | 0% | 2.32 |
| standard | random | 0% | 1.41 | 100% | nan | 450.6 | 0% | 0.28 |
| decoys | bayesian | 100% | 0.0 | 96% | 92.7 | 101.4 | 0% | 1.88 |
| decoys | bayesian@2 | 100% | 0.0 | 100% | 70.6 | 151.9 | 0% | 1.76 |
| decoys | bayesian-naive | 64% | 0.0 | 32% | 167.3 | 249.1 | 4% | 1.92 |
| decoys | greedy | 16% | 1.0 | 96% | 187.2 | 421.4 | 0% | 1.4 |
| decoys | random | 0% | 2.83 | 84% | nan | 450.6 | 0% | 0.28 |
| harsh | bayesian | 100% | 0.0 | 100% | 105.5 | 111.8 | 0% | 0.8 |
| harsh | bayesian@2 | 100% | 0.0 | 100% | 76.1 | 157.8 | 0% | 0.88 |
| harsh | bayesian-naive | 76% | 0.0 | 64% | 124.1 | 177.0 | 4% | 0.6 |
| harsh | greedy | 24% | 1.0 | 100% | 151.2 | 347.5 | 0% | 1.0 |
| harsh | random | 0% | 2.83 | 100% | nan | 393.1 | 0% | 0.08 |

## Confidence calibration

87 missions with a tight time budget ended without visual contact, so the agent had to report an estimate. Brier score of the reported P(EVE within 1 cell): 0.1192 (0 = perfect).

| reported P bin | missions | mean reported | observed hit rate |
|---|---|---|---|
| 0.0-0.2 | 33 | 0.097 | 0.03 |
| 0.2-0.4 | 23 | 0.291 | 0.13 |
| 0.4-0.6 | 14 | 0.494 | 0.143 |
| 0.6-0.8 | 11 | 0.7 | 0.636 |
| 0.8-1.0 | 6 | 0.868 | 1.0 |
