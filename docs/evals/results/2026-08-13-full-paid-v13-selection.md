# LiveBench Hermes evaluation: v13 selection cohort

> **Result:** `moa_mimo` scored **0.7664** versus **0.7280** for `base` on 149/150 common-valid pairs. The paired delta was **+0.0384**, but its normal-approximation 95% CI **[-0.0126, 0.0894]** crossed zero. The six output-blind replacements escaped ceiling saturation, although the two CTA candidates exposed floor saturation instead.

## Run summary

| Field | Value |
|---|---|
| Run ID | `full-paid-v13-20260813T132201Z` |
| Experiment ID | `livebench-hermes-hard-cohort-15x10-v13-selection` |
| Release | `2026-06-25` |
| Scenarios | 15 |
| Samples per scenario | 10 |
| Arms | `base`, `moa_mimo` |
| Executed cells | 300/300 |
| Planned pairs | 150 |
| Common-valid pairs | **149 (99.33%)** |
| Excluded pairs | 1 |
| Score records | 298 |

This is selection evidence, not independent confirmation: six scenarios were selected to replace exact-ceiling instances observed in v10, and the recommended one-sample selection pilot was skipped before this full run.

## Overall results

| Arm | Mean | Delta vs `base` | 95% CI for arm mean | n |
|---|---:|---:|---:|---:|
| `moa_mimo` | **0.7664** | +0.0384 | [0.7106, 0.8222] | 149 |
| `base` | **0.7280** | — | [0.6642, 0.7919] | 149 |

The paired score-difference interval for `moa_mimo - base` was **[-0.0126, 0.0894]**. It crosses zero, so the observed ranking is not confirmatory evidence of superiority.

## Category results

| Category | Common pairs | `base` | `moa_mimo` |
|---|---:|---:|---:|
| Data Analysis | 70 | **0.6889** | 0.6511 |
| Math | 59 | 0.6925 | **0.8240** |
| Instruction Following | 10 | 0.9400 | **1.0000** |
| Language | 10 | **1.0000** | **1.0000** |

The overall MoA advantage is concentrated in mathematics. Data Analysis moved in the opposite direction.

## Scenario results

| Family | ID | n | `base` | `moa_mimo` | Selection note |
|---|---|---:|---:|---:|---|
| `paraphrase` | `8c22986a` | 10 | 0.9400 | 1.0000 | retained, near ceiling |
| `math_comp` | `a84e6c88` | 10 | 0.9000 | 0.9000 | retained |
| `olympiad` | `2dd75e08` | 10 | **0.8917** | 0.8292 | retained |
| `olympiad` | `11f95734` | 10 | 0.1191 | **0.7830** | retained, highly discriminating |
| `olympiad` | `e5b72d9c` | 10 | 0.6775 | **0.9475** | retained |
| `olympiad` | `527d5f9f` | 10 | 0.8250 | **0.8583** | replacement; useful headroom |
| `olympiad` | `2a82215e` | 9 | **0.7473** | 0.6039 | replacement; useful headroom |
| `connections` | `27662d96` | 10 | 1.0000 | 1.0000 | exact ceiling; replace |
| `tablejoin` | `d8958419` | 10 | 1.0000 | 0.9800 | retained, near ceiling |
| `tablejoin` | `a783dc96` | 10 | 0.8260 | **0.9210** | retained |
| `tablejoin` | `539fd067` | 10 | 0.8390 | **0.9400** | retained |
| `tablejoin` | `2e645a9a` | 10 | **0.9570** | 0.9430 | replacement; near ceiling |
| `tablejoin` | `4d351c29` | 10 | **1.0000** | 0.7740 | replacement; discriminating |
| `cta` | `58223a1f` | 10 | 0.0000 | 0.0000 | replacement; exact floor, replace |
| `cta` | `d3d91018` | 10 | **0.2000** | 0.0000 | replacement; near floor, replace |

### Saturation outcome

Under the strict exact-ceiling definition, only `27662d96` remained saturated. None of the six new candidates was exact-ceiling. However, `58223a1f` was exact-floor and `d3d91018` was near-floor. They provide little useful discrimination and should not enter a confirmation cohort. The two new `olympiad` instances and `4d351c29` are the strongest replacements; `2e645a9a` is usable but near ceiling.

## Reliability and OpenRouter-limit audit

| Metric | Value |
|---|---:|
| Valid cells | 299 |
| Excluded cells | 1 |
| `INVALID_MOA_TRACE` | 1 |
| Provider errors | 0 |
| Timeouts | 0 |
| Attempt-2 journals | 0 |
| Valid MoA traces | 149 |
| Invalid MoA traces | 1 |
| Reference calls | 149 |
| Reference input tokens | 49,566 |
| Reference output tokens | 1,897,693 |

The accidental OpenRouter spending-limit change produced no recorded provider failure. Every cell ran once; no retry was needed or performed. The sole exclusion was an invalid MoA trace, not a billing, rate-limit, or provider error.

## Recommendation

Do not treat v13 as a confirmation cohort. For the next selection revision:

1. retain both new `olympiad` scenarios and `4d351c29`;
2. replace exact-ceiling `27662d96`;
3. replace both CTA floor cases;
4. consider replacing near-ceiling `2e645a9a` and `d8958419` if the goal is maximum discrimination;
5. run a one-sample pilot before any further ten-sample paid confirmation.

## Reproducibility

The report was reconstructed from:

- `runs/full-paid-v13-20260813T132201Z/generations/scoring/*/summary.json`;
- `runs/full-paid-v13-20260813T132201Z/generations/scoring/*/scores.json`;
- `runs/full-paid-v13-20260813T132201Z/cells/*.json`;
- `runs/full-paid-v13-20260813T132201Z/attempts/*.json`;
- the frozen manifest, config snapshot, and question records in the run directory.

Raw run evidence remains local and is not committed.
