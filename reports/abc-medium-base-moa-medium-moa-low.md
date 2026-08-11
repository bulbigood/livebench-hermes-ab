# LiveBench ABC — BASE medium vs MoA medium vs MoA low

**Status:** `VALID_ABC_ON_49_COMMON_CELLS`

## Headline

| Comparison | Left | Right | Sample delta | Task delta | Task-cluster 95% | W/T/R |
|---|---:|---:|---:|---:|---:|---:|
| A → B | 0.9002 | 0.9685 | +0.0683 | +0.0825 | [+0.0000, +0.2388] | 6/43/0 |
| A → C | 0.9002 | 0.9572 | +0.0570 | +0.0678 | [+0.0000, +0.1865] | 6/43/0 |
| C → B | 0.9572 | 0.9685 | +0.0112 | +0.0148 | [-0.0120, +0.0563] | 3/43/3 |

## Latency on 49 common cells

- A BASE medium: mean 34.9s, total 1709.3s
- B MoA medium: mean 94.6s, total 4636.5s
- C MoA low: mean 98.6s, total 4830.8s

## Per-task B minus C deltas

- `language/connections/181616b71589`: +0.0000
- `instruction_following/summarize/1a06f223c798`: +0.0000
- `math/math_comp/504e4f0317a2`: +0.0000
- `reasoning/zebra_puzzle/6bd178380f18`: +0.1875
- `instruction_following/paraphrase/a365e843fd01`: +0.0000
- `data_analysis/tablereformat/bfe58cf09204`: +0.0000
- `instruction_following/story_generation/c0e4dc6b1c4c`: +0.0000
- `language/connections/c94b09d2821d`: +0.0000
- `reasoning/spatial/d968c11d5c59`: +0.0000
- `data_analysis/tablejoin/dc753a46614f`: -0.0400

## Interpretation

B versus C isolates aggregator reasoning effort while preserving MoA references. A versus either MoA arm is a compound comparison against BASE.

C has 50 valid outputs, but the headline intersection is 49 because A/B lacks one zebra sample.
