# Likelihood tempering ablation

Calibration: 100 held-out missions with a 60-step budget (scored only when they end without contact). Success/time: 12 decoys + 12 harsh missions.

| tau | missions | Brier | mean reported P | observed hit rate | mid-range (0.2-0.8) reported | mid-range observed | success | mean time |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 87 | 0.1457 | 0.344 | 0.310 | 0.45 | 0.38 | 100% | 88 |
| 0.7 | 88 | 0.1633 | 0.256 | 0.295 | 0.44 | 0.41 | 100% | 77 |
| 0.5 | 94 | 0.1429 | 0.226 | 0.277 | 0.43 | 0.53 | 100% | 102 |
| 0.35 | 92 | 0.1795 | 0.175 | 0.337 | 0.36 | 0.65 | 100% | 103 |
