# LiveBench Hermes BASE vs MoA — medium, 10 new tasks × 5 samples

**Status:** `VALID_WITH_ONE_INFRA_EXCLUSION`  
**Verdict:** `PROMISING_NOT_GENERAL`

## Headline

- Scored pairs: 49/50 (one infrastructure timeout excluded by operator authorization).
- BASE mean: 0.9002
- MoA mean: 0.9685
- Sample-weighted delta: +0.0683
- Equal-task-weighted delta: +0.0825
- Task-cluster bootstrap 95% interval: [+0.0000, +0.2388]
- Sample wins/ties/regressions: 6/43/0
- Task wins/ties/regressions: 2/8/0

## Per task

| Category | Task | n | BASE | MoA | Delta | SD(delta) | W/T/R |
|---|---|---:|---:|---:|---:|---:|---:|
| language | connections | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| instruction_following | summarize | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| math | math_comp | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| reasoning | zebra_puzzle | 4 | 0.0000 | 0.7812 | +0.7812 | 0.4375 | 4/0/0 |
| instruction_following | paraphrase | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| data_analysis | tablereformat | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| instruction_following | story_generation | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| language | connections | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| reasoning | spatial | 5 | 1.0000 | 1.0000 | +0.0000 | 0.0000 | 0/5/0 |
| data_analysis | tablejoin | 5 | 0.8220 | 0.8660 | +0.0440 | 0.0602 | 2/3/0 |

## Latency and telemetry

- BASE total wall time: 1709.3s
- MoA total wall time: 4636.5s
- MoA overhead: +2927.2s (+171.2%)
- Valid Minimax references: 49/49
- Minimax usage: 49189 input / 204976 output tokens
- Main-model token telemetry is incomplete; no USD cost is inferred.

## Interpretation

MoA improved six samples and regressed none, but only two of ten tasks improved. Most lift came from one zebra-puzzle task; eight tasks tied. The interval touches zero under task-cluster resampling. This supports targeted use for difficult symbolic reasoning, not general adoption.

The excluded zebra sample timed out before either arm answer was persisted. The remaining four zebra samples are paired and included. No model output was rerun or selected by score.
