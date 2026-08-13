# Hard cohort selection — v10

The `livebench-hermes-hard-cohort-15x10-v10` matrix keeps the experiment budget fixed at **15 scenarios × 10 samples × 4 arms = 600 cells**, with at most **900 provider calls**.

## Why the cohort changed

The 2026-08-13 run showed broad ceiling effects in the selected instruction-following and zebra-puzzle instances. Official `2026-06-25` leaderboard distributions also show `zebra_puzzle`, `spatial`, and `tablereformat` near saturation. The replacement cohort therefore removes those families rather than merely choosing longer prompts from the same saturated pool.

Candidates were selected without inspecting model generations or candidate scores. Selection used release eligibility, deterministic scorer availability, family-level leaderboard headroom, and structural metadata. The new cohort is a selection candidate, not yet a confirmation result.

## Composition

| Category | Family | Scenarios | Selection basis |
|---|---|---:|---|
| Instruction Following | `simplify` | 1 | dense deterministic constraint composition |
| Instruction Following | `paraphrase` | 1 | dense deterministic constraint composition |
| Instruction Following | `story_generation` | 1 | dense deterministic constraint composition |
| Math | `math_comp` | 3 | one active SMC and two active AIME records |
| Math | `olympiad` | 3 | active IMO/USAMO proof-rearrangement records |
| Language | `connections` | 3 | active deterministic grouping puzzles |
| Data Analysis | `tablejoin` | 3 | large schema/mapping cases from the hardest runnable family distribution |

## Scoring safeguards

The local adapter now explicitly dispatches `math_comp`, `olympiad`, `cta`, and `connections` through the pinned upstream deterministic scorers. Unknown families fail before paid execution. `prepare` invokes this validation after selection and before creating a runnable matrix.

`AMPS_Hard` was not selected. Its pinned evaluator can invoke an LLM fallback when symbolic equivalence is inconclusive, which violates the intended deterministic offline scoring contract. `cta` is supported and tested but omitted to preserve the fixed 15-scenario limit and a balanced primary cohort.

## Evidence and boundaries

- Pinned LiveBench release: `2026-06-25`.
- Pinned upstream commit: `00eae856aa1c1a9e9d058a65a9a94d85884034c4`.
- Release and removal lifecycle checks are enforced by the harness.
- Known-ground-truth scorer sanity checks run in the test suite.
- A successful v10 `prepare` confirmed 600 cells and 900 expected provider calls.
- No candidate model outputs were used to choose these records.
- Difficulty and discrimination remain hypotheses until a paid run is scored.
