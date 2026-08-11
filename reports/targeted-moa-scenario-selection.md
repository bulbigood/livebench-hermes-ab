# Targeted LiveBench scenario selection for MoA A/B testing

## Decision

The next frozen cohort contains 15 question instances: five each from Instruction Following, Reasoning, and Data Analysis. Math, Language, Coding, and all other categories are excluded from this experiment config. Historical runs and reports remain unchanged.

Selection was output-blind: prior BASE/MoA scores were not used to rank new candidates. Existing target-category questions were retained for continuity; additions were chosen from structural difficulty signals and active-snapshot eligibility.

## Sources and evidence boundary

- [LiveBench paper](https://arxiv.org/abs/2406.19314): LiveBench uses frequently updated, contamination-limited questions and objective ground-truth scoring; it includes harder variants of tasks from IFEval and Big-Bench Hard.
- [LiveBench leaderboard](https://livebench.ai/): public category and model aggregates.
- [Official 2026-06-25 subtask table](https://livebench.ai/table_2026_06_25.csv): family-level scores for 40 published model rows.
- [Official 2026-06-25 task manifest](https://livebench.ai/categories_2026_06_25.json): release-specific category/family schema.
- [Pinned LiveBench repository](https://github.com/LiveBench/LiveBench): task definitions and objective scorers.
- Local corpus snapshot: release cutoff `2026-06-25`, upstream commit `00eae856aa1c1a9e9d058a65a9a94d85884034c4`.

No reliable published instance-level leaderboard was found for these exact question IDs. Therefore instance selection uses explicit, output-blind proxies: declared puzzle level, number and diversity of verifiable instructions, prompt/schema size, number of entities or candidate columns, structured-output burden, and active-snapshot status.

### Published family-level difficulty

Across the 40 model rows in the official release table:

| Family | Median | Best | Interpretation |
|---|---:|---:|---|
| `tablejoin` | 47.384 | 56.135 | Hardest active target family by a wide margin |
| `simplify` | 61.792 | 75.700 | Hardest Instruction Following family |
| `paraphrase` | 65.334 | 79.867 | Substantial headroom remains |
| `summarize` | 69.100 | 88.233 | Moderate family-level difficulty |
| `story_generation` | 69.275 | 80.600 | Moderate difficulty with synthesis risk |
| `zebra_puzzle` | 92.750 | 100.000 | High aggregate; selected level-20 items target its hard tail |
| `spatial` | 98.000 | 100.000 | Near saturation; useful as a negative control |
| `tablereformat` | 98.039 | 100.000 | Near saturation; useful as a mechanical exactness control |

`cta` is active in the pinned local corpus but absent from the public 2026-06-25 table, so no public score is assigned to it here. These scores rank families, not exact question instances.

## Complete available task-family inventory

| Category | Family | Corpus rows | Active rows | What it tests |
|---|---|---:|---:|---|
| Instruction Following | `summarize` | 100 | 50 | Content compression while satisfying exact lexical, length, section, and boundary constraints |
| Instruction Following | `simplify` | 100 | 50 | Simplification without violating independently checked formatting and lexical constraints |
| Instruction Following | `paraphrase` | 100 | 50 | Semantic preservation plus exact output constraints |
| Instruction Following | `story_generation` | 100 | 50 | Long-form generation under simultaneous content and format constraints |
| Reasoning | `zebra_puzzle` | 100 | 50 | Multi-attribute constraint satisfaction and exact entity assignment |
| Reasoning | `spatial` | 50 | 50 | Geometric/spatial deduction with exact short answers |
| Reasoning | `web_of_lies_v2` | 50 | 0 | Nested truthfulness reasoning; retired from the active snapshot on `2025-04-02` |
| Data Analysis | `cta` | 50 | 50 | Column-type annotation from sparse samples and many semantically similar labels |
| Data Analysis | `tablejoin` | 50 | 50 | Schema matching between noisy tables and exact join-map construction |
| Data Analysis | `tablereformat` | 50 | 50 | Lossless conversion between table serializations |

There are only four active Instruction Following families, two active Reasoning families, and three active Data Analysis families. Five scenarios per category therefore means five question instances, not five distinct families.

## Frozen 15-scenario cohort

### Instruction Following — five scenarios

| Family | Question ID prefix | Blind difficulty signal | Why retained/selected |
|---|---|---|---|
| `summarize` | `1a06f223c7988766` | 6 independent instruction checks | Existing continuity item; combines forbidden/required words, bullets, postscript, sentence count, and sections |
| `summarize` | `469c2a921e910fce` | 6 independent instruction checks | Highest constraint count; complementary mix of quotation, word/paragraph counts, bullets, and exact ending |
| `simplify` | `0503923535fbd8ba` | 6 independent instruction checks | Adds the only missing active IF family and combines semantic simplification with six exact checks |
| `paraphrase` | `a365e843fd014371` | 5 independent instruction checks; 2,583-character prompt | Existing continuity item; tests semantic preservation under title, paragraph, lexical, and ending constraints |
| `story_generation` | `c0e4dc6b1c4cca07` | 5 independent instruction checks | Existing continuity item and the most constrained active story-generation question |

This category deliberately covers all four active families. The second `summarize` instance is included because it has the joint-highest active constraint count and a different checker composition from the retained summary.

### Reasoning — five scenarios

| Family | Question ID prefix | Blind difficulty signal | Why retained/selected |
|---|---|---|---|
| `zebra_puzzle` | `c29eb6b3c9fd3f67` | Declared level 20; 5,159-character prompt; five people and five attribute classes | Highest structural burden among active zebra questions |
| `zebra_puzzle` | `6bd178380f1808ea` | Declared level 20; 3,535-character prompt; five people and five attribute classes | Existing continuity item with a long constraint chain |
| `zebra_puzzle` | `c833574b0ff6e860` | Declared level 20; 2,869-character prompt | Top-level active puzzle with a different attribute combination |
| `zebra_puzzle` | `2102018493646d36` | Declared level 20; 2,557-character prompt | Top-level active puzzle selected before model outputs |
| `spatial` | `d968c11d5c594e03` | 701-character geometric construction with an exact numeric answer | Existing continuity item; preserves the only other active Reasoning family |

All four zebra instances have the maximum declared active level, 20. `web_of_lies_v2` was considered but rejected because all of its rows are retired in the pinned snapshot. The 4:1 family skew is disclosed rather than hidden: current LiveBench simply offers only two active Reasoning families.

### Data Analysis — five scenarios

| Family | Question ID prefix | Blind difficulty signal | Why retained/selected |
|---|---|---|---|
| `cta` | `58223a1f18c3cda8` | 6,848-character prompt; sparse/NaN sample; many near-duplicate labels | Hardest active CTA by prompt/candidate-list size |
| `cta` | `d3d910189e70e5e5` | 6,100-character prompt; many near-duplicate labels | Second-largest active CTA and complementary hospital-data label space |
| `tablejoin` | `dc753a46614f7f4d` | 4,466-character prompt; 162-character exact mapping | Existing continuity item and largest active join prompt |
| `tablejoin` | `bd4b2031ad50538f` | 4,098-character prompt; 109-character exact mapping | Second-largest active join prompt; adds another schema-alignment case |
| `tablereformat` | `bfe58cf09204ef9d` | 3,433-character source; 3,045-character exact ground truth | Existing continuity item and largest active reformat prompt |

The 2:2:1 allocation emphasizes semantic ambiguity (`cta`, `tablejoin`) while retaining one large lossless transformation case. This is more diagnostic for MoA than filling the cohort with mechanically similar reformat cases.

## Why these scenarios are suitable for MoA A/B testing

MoA can help only where an independent reference has useful information that the aggregator can verify or reconcile. The cohort targets three different mechanisms:

1. **Constraint auditing — Instruction Following.** A reference can identify missed lexical, length, boundary, and formatting requirements. Multiple simultaneous objective checks make improvements measurable without an LLM judge.
2. **Independent deduction — Reasoning.** Zebra and spatial questions permit a reference to solve or cross-check a constraint chain. Exact ground truth limits stylistic ambiguity.
3. **Schema alignment — Data Analysis.** CTA and table-join tasks benefit from alternative interpretations of ambiguous labels and columns; table reformat tests whether extra context helps without corrupting a deterministic transformation.

The cohort also contains failure opportunities for MoA: verbose advice can distract the aggregator, conflicting mappings can be copied, and already-easy deterministic tasks may show no gain while increasing latency. That makes the test diagnostic rather than promotional.

## Frozen experiment contract

- Config: `config/experiment-targeted-moa-15x5.yaml`
- Categories: exactly `instruction_following: 5`, `reasoning: 5`, `data_analysis: 5`
- Samples: 5 per scenario
- Paired units: 75
- BASE calls: 75
- MoA aggregator calls: 75
- Minimax M3 reference calls: 75
- Nominal total: 225 model calls
- Main model: `openai-codex:gpt-5.6-sol`, reasoning `medium` in both arms
- MoA reference: `openrouter:minimax/minimax-m3`
- Tools disabled; objective LiveBench scorers; no judge calls
- Timeout: 1,800 seconds; retries disabled

## Limitations

- Published evidence does not provide stable per-question difficulty values for these exact IDs, so structural proxies are necessary.
- Reasoning diversity is constrained by the current snapshot: only zebra and spatial remain active.
- Long prompts are not automatically difficult; length is used only alongside task-specific signals.
- Five scenarios per category improve balance but remain too few for strong category-wide inference. Results must retain task-cluster uncertainty and per-task disclosure.
