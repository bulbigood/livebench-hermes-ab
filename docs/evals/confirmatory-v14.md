# Confirmatory cohort v14

V14 is frozen for a future full paid comparison of `base` and `moa_mimo`. The full configuration uses **15 scenarios × 20 samples × 2 arms = 600 cells**, with at most **900 provider calls**. Running the CLI without `--full` remains a one-sample smoke test.

## Selection boundary

The completed v13 run was treated as selection evidence. Three unusable scenarios were removed:

- `58223a1f` (`cta`): exact floor, 0.0 for both arms;
- `d3d91018` (`cta`): near floor, 0.2 for `base` and 0.0 for `moa_mimo`;
- `27662d96` (`connections`): exact ceiling, 1.0 for both arms.

Candidate eligibility was frozen before inference: active in release `2026-06-25`, supported by a deterministic scorer, no CTA or connections tasks, and structural headroom within `olympiad` or `tablejoin`. Six candidates were evaluated in a separate one-sample paid pilot: 12 cells and at most 18 provider calls.

## Pilot results

| Candidate | Family | `base` | `moa_mimo` | Decision |
|---|---|---:|---:|---|
| `6dfb6aad` | `olympiad` | 0.0213 | 0.6809 | accept |
| `0499deda` | `olympiad` | 0.0161 | 0.8710 | accept |
| `d4b2efd5` | `tablejoin` | 0.8000 | 0.3300 | accept |
| `dc753a46` | `tablejoin` | 0.9100 | 0.8000 | reserve |
| `d805a5c9` | `olympiad` | 1.0000 | 0.9750 | reject: near ceiling |
| `bd4b2031` | `tablejoin` | unavailable | unavailable | reject: invalid MoA trace |

Acceptance required a pooled pilot score between 0.15 and 0.95 and an absolute cross-arm spread of at least 0.05. Pilot outputs select scenarios only; they are not confirmation evidence.

## Sample count

The v13 paired delta was +0.03836 with paired-difference standard deviation 0.31770. Under the simplifying assumption that this effect and variance persist, 20 samples across 15 scenarios provide 300 planned pairs and project a two-sided 95% paired-CI lower bound near +0.0024. This is a planning estimate, not a guarantee. The full v14 run must be interpreted from its own frozen evidence.

## Verification contract

- Experiment ID: `livebench-hermes-confirmatory-15x20-v14`.
- Hermes compatibility profile: `0.19.1`.
- Pinned upstream commit: `00eae856aa1c1a9e9d058a65a9a94d85884034c4`.
- Full run: 600 cells, at most 900 provider calls.
- Smoke run: 30 cells, at most 45 provider calls.
- Primary endpoint: mean paired score difference, `moa_mimo - base`.
- Success criterion: lower bound of the two-sided 95% paired confidence interval is strictly greater than zero.
- Reliability remains separate: common-valid coverage, invalid-trace rate, timeout rate, and provider-error rate.
