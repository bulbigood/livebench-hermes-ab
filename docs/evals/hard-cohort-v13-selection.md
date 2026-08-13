# Saturation refresh: v13 selection cohort

V13 replaces the six scenarios that were exactly saturated when the completed v10 evidence is restricted to the current `base` and `moa_mimo` arms. It keeps 15 scenarios, 10 samples, and 2 arms: 300 cells and at most 450 provider calls.

## Saturated v10 scenarios under current arms

A scenario is marked saturated here only when both current arms scored exactly 1.0 on every common-valid sample for that scenario.

| Removed ID | Family | Common-valid n | `base` | `moa_mimo` |
|---|---|---:|---:|---:|
| `05039235` | `simplify` | 9 | 1.0000 | 1.0000 |
| `c0e4dc6b` | `story_generation` | 10 | 1.0000 | 1.0000 |
| `b241aac6` | `math_comp` | 10 | 1.0000 | 1.0000 |
| `504e4f03` | `math_comp` | 10 | 1.0000 | 1.0000 |
| `d1fa30fd` | `connections` | 10 | 1.0000 | 1.0000 |
| `7327ff4c` | `connections` | 9 | 1.0000 | 1.0000 |

Near-ceiling but non-saturated scenarios were retained. This avoids converting a focused exact-ceiling refresh into an unbounded redesign.

## Output-blind replacements

Replacement quotas were declared before any candidate-model inference. Candidate ranking used only pinned-release eligibility, deterministic scorer support, family-level headroom from the v10 evidence, and task structure. No candidate outputs or candidate scores were used.

| Added ID | Family | Structural reason |
|---|---|---|
| `527d5f9f` | `olympiad` | high expression count and full proof-rearrangement scorer support |
| `2a82215e` | `olympiad` | high expression count and long proof prompt |
| `2e645a9a` | `tablejoin` | largest active join mapping by mapped-column count |
| `4d351c29` | `tablejoin` | next-largest active join mapping |
| `58223a1f` | `cta` | long active CTA record with deterministic scorer |
| `d3d91018` | `cta` | second long active CTA record with deterministic scorer |

The refresh deliberately reallocates saturated instruction-following, `math_comp`, and `connections` slots to families with observed or official headroom. It is not family-balanced; discrimination is prioritized over cosmetic symmetry.

## Verification and acceptance boundary

- Pinned release: `2026-06-25`.
- Pinned upstream commit: `00eae856aa1c1a9e9d058a65a9a94d85884034c4`.
- Every replacement is active in the pinned release.
- Known-ground-truth deterministic scorer checks return 1.0 for all six replacements.
- Free `prepare` confirms 15 scenarios, 300 cells, and 450 expected provider calls.
- The next paid step should be the default one-sample selection pilot, not a ten-sample confirmation run.
- A candidate should be replaced again if both arms score exactly 1.0 in that pilot. Pilot outputs must not be presented as confirmation evidence.
