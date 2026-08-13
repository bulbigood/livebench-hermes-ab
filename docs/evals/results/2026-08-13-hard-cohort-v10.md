# LiveBench Hermes evaluation — hard cohort v10

> **Result:** `moa_minimax` ranked first on the common-valid cohort at **0.9494**, only **0.0005** above `moa_mimo` at **0.9489**. The hard cohort improved discrimination in several scenarios, but six of fifteen remained fully saturated and paired coverage fell to **119/150 (79.33%)**.

## Run summary

| Field | Value |
|---|---|
| Run ID | `hard-cohort-preflight-20260813T1125Z` |
| Experiment ID | `livebench-hermes-hard-cohort-15x10-v10` |
| Release | `2026-06-25` |
| Scenarios | 15 |
| Samples per scenario | 10 |
| Arms | 4 |
| Executed cells | 600/600 |
| Planned comparison pairs | 150 |
| Common-valid comparison pairs | **119 (79.33%)** |
| Excluded pairs | 31 |
| Score records in common cohort | 476 |

The primary analysis uses the intersection where all four arms produced a valid cell. It therefore compares every arm on the same 119 scenario/sample pairs.

## Overall results

| Rank | Arm | Mean | Delta vs `base` | 95% CI for arm mean | Paired-delta 95% CI vs base | n |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `moa_minimax` | **0.9494** | +0.0276 | [0.9272, 0.9716] | [-0.0089, 0.0641] | 119 |
| 2 | `moa_mimo` | **0.9489** | +0.0271 | [0.9273, 0.9705] | [-0.0114, 0.0657] | 119 |
| 3 | `gpt_medium` | **0.9256** | +0.0038 | [0.8881, 0.9631] | [-0.0281, 0.0358] | 119 |
| 4 | `base` | **0.9218** | — | [0.8818, 0.9617] | — | 119 |

The paired-delta intervals are normal-approximation diagnostics over pairwise score differences. Every interval crosses zero. The run therefore gives a ranking, but not confirmatory evidence that an arm beats `base`. The difference between the two MoA arms is practically negligible at **0.00047**.

## Results by category

| Category | Common pairs | `base` | `gpt_medium` | `moa_minimax` | `moa_mimo` |
|---|---:|---:|---:|---:|---:|
| Instruction Following | 28 | 0.9786 | **1.0000** | **1.0000** | **1.0000** |
| Math | 45 | 0.8629 | 0.8848 | 0.9135 | **0.9188** |
| Language | 18 | **1.0000** | **1.0000** | **1.0000** | 0.9630 |
| Data Analysis | 28 | 0.9093 | 0.8689 | 0.9239 | **0.9371** |

## Results by scenario

Means use only common-valid samples for the scenario.

| Family | ID | n | `base` | `gpt_medium` | `moa_minimax` | `moa_mimo` |
|---|---|---:|---:|---:|---:|---:|
| `simplify` | `05039235` | 8 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `paraphrase` | `8c22986a` | 10 | 0.9400 | 1.0000 | 1.0000 | 1.0000 |
| `story_generation` | `c0e4dc6b` | 10 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `math_comp` | `b241aac6` | 10 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `math_comp` | `504e4f03` | 7 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `math_comp` | `a84e6c88` | 4 | 1.0000 | 1.0000 | 0.7500 | 1.0000 |
| `olympiad` | `2dd75e08` | 9 | 0.9028 | 0.9028 | **0.8889** | 0.8750 |
| `olympiad` | `11f95734` | 7 | 0.3009 | 0.4347 | **0.7903** | 0.6960 |
| `olympiad` | `e5b72d9c` | 8 | 0.9500 | **0.9563** | 0.9469 | 0.9500 |
| `connections` | `27662d96` | 7 | 1.0000 | 1.0000 | **1.0000** | 0.9048 |
| `connections` | `d1fa30fd` | 5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `connections` | `7327ff4c` | 6 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `tablejoin` | `d8958419` | 9 | **1.0000** | **1.0000** | 0.9689 | 0.9722 |
| `tablejoin` | `a783dc96` | 9 | 0.7178 | 0.7156 | 0.8700 | **0.9389** |
| `tablejoin` | `539fd067` | 10 | **1.0000** | 0.8890 | 0.9320 | 0.9040 |

## Difficulty and discrimination

The replacement improved the useful headroom in a few places:

- `11f95734` is the strongest discriminator. Its arm means range from 0.3009 to 0.7903.
- `a783dc96` separates the MoA arms from both non-MoA arms and has a 0.2233 full range.
- `2dd75e08` and `e5b72d9c` avoid exact saturation, although their between-arm separation is small.
- `539fd067` produces non-trivial differences, but `base` remains perfect and the ordering is not monotonic with model complexity.

Six scenarios are still fully saturated on the common-valid cohort: `05039235`, `c0e4dc6b`, `b241aac6`, `504e4f03`, `d1fa30fd`, and `7327ff4c`. `a84e6c88` is also nearly saturated and has only four common-valid samples. The current cohort is therefore harder than the previous one in selected families, but it is not yet an efficient 15-scenario discrimination set.

## Exclusions and trace audit

| Exclusion | Cells |
|---|---:|
| `INVALID_MOA_TRACE` | 26 |
| `CELL_TIMEOUT` | 5 |

| Arm | Timeouts | Invalid traces | Total excluded cells |
|---|---:|---:|---:|
| `base` | 0 | 0 | 0 |
| `gpt_medium` | 0 | 0 | 0 |
| `moa_minimax` | 5 | 22 | 27 |
| `moa_mimo` | 0 | 4 | 4 |

Invalid-trace details were 14 cases of missing reference-output usage and 12 empty or degraded references. The trace audit recorded 269 valid traces, 26 invalid traces, 269 reference calls, 215,585 reference-input tokens, and 2,877,463 reference-output tokens.

The concentration of 27/31 excluded cells in `moa_minimax` is a material reliability difference. Common-valid scoring keeps the primary arm comparison fair, but it also removes those failed pairs and reduces coverage. Reliability and score quality should therefore be reported separately rather than folding failures into an invented score.

## Statistical diagnostics

- Minimum common-valid samples in any scenario: **4**.
- Configured confidence level: **95%**.
- Target margin of error: **±0.05**.
- The harness marked the pilot as insufficient for a sample-count recommendation because the minimum per-scenario common coverage is below five.

## Comparison with the previous cohort

The previous v9 run had 139/150 common-valid pairs (92.67%) and was won by `moa_mimo` at 0.9285. This v10 run has 119/150 pairs (79.33%) and is narrowly won by `moa_minimax` at 0.9494.

These absolute means and rankings are **not a direct confirmatory comparison**: the scenario cohort changed. The justified conclusions are narrower:

1. v10 introduced substantially more headroom in the selected olympiad and tablejoin records.
2. It also introduced worse MoA trace/timeout coverage, especially for `moa_minimax`.
3. Six replacement scenarios remain saturated, so further output-blind replacement is warranted before treating this as a stable confirmation suite.
4. The MoA score advantage over `base` is directionally positive, but paired uncertainty remains too wide for a confirmatory claim.

## Reproducibility

This report was reconstructed from immutable local artifacts:

- `runs/hard-cohort-preflight-20260813T1125Z/manifest.json`
- `runs/hard-cohort-preflight-20260813T1125Z/cells/*.json`
- `runs/hard-cohort-preflight-20260813T1125Z/generations/scoring/246b92b825294b71b0d486864f016fef/summary.json`
- `runs/hard-cohort-preflight-20260813T1125Z/generations/scoring/246b92b825294b71b0d486864f016fef/scores.json`

The `runs/` directory remains local evidence and is not committed. This Markdown file is the repository-safe result summary.
