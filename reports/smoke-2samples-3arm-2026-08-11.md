# Three-arm 2-sample smoke — 2026-08-11

## Verdict

**INVALID_REFERENCE_DEGRADATION**

The complete synchronized matrix ran and scored locally, but 9 of 60 MoA reference calls produced the Hermes `(empty response)` sentinel after exhausting the 10,000-token reference budget on hidden reasoning. The pre-fix validator incorrectly treated the sentinel as substantive output. Therefore the scores below are exploratory diagnostics, not valid comparative benchmark evidence.

A deterministic validator fix now rejects this run during scoring with:

```text
ERROR: trace 1: degraded reference output
```

No judge-model calls were used.

## Run identity

- source commit: `f1a45975e71f32d0d3632e557d47b02b98aa02ee`
- local run: `runs/smoke-2samples-f1a4597`
- Hermes executable: `/tmp/livebench-hermes-public-0.19.1/.venv/bin/hermes`
- Hermes version: `0.19.1` (`verified` compatibility profile)
- Hermes source commit: `dac4bbea09a342879d9769d6a5357b12b84b936c`
- Hermes executable SHA-256: `17feb23bb5efa7952d6b970ee26a4628e0615ba12a4061abb9495b8875fcac12`
- config SHA-256: `939734e260b6c6f6660d5d09fdd8a5279cf931add7ac4c757909cfbda201b55b`
- scenario SHA-256: `104d76b714b4d1dc3b41340b33a2996b126099fc1f38aab9a9829448019051af`
- questions SHA-256: `b474412875143207e96e4114fac94f5e18389255605b18f9df87a8fbcf3d14a9`
- manifest SHA-256: `69c1f5747058161d3d6b5a1383100c2376024718d8570a634e7e63c9e31c4ee3`

An independent no-cost postflight `prepare` reproduced the config, scenario, and questions hashes exactly.

## Matrix integrity

- scenarios: 15
- samples per scenario: 2
- paired cells: 30
- arms: 3
- arm-cell invocations: 90
- nominal provider requests: 150
- completed records: 30 per arm
- duplicate or missing `(question_id, sample_index, pair_id)` cells: 0
- ordering differences between arms: 0
- empty final outputs: 0
- exclusions: 0

All arms used the same ordered 30-cell matrix. Persisted `pair_id`, `question_id`, and `sample_index` values matched the frozen manifest exactly.

## Runtime model provenance

| Arm | Main runtime | Reference runtime | Aggregator runtime |
|---|---|---|---|
| `base` | `openai-codex / gpt-5.6-sol`, reasoning `medium` | — | — |
| `moa_minimax` | `moa / default` | `openrouter / minimax/minimax-m3` | `openai-codex / gpt-5.6-sol`, reasoning `medium` |
| `moa_mimo` | `moa / default` | `openrouter / xiaomi/mimo-v2.5` | `openai-codex / gpt-5.6-sol`, reasoning `medium` |

Evidence came from the source config, generated per-arm Hermes configs, manifest effective settings, 90 raw runtime records, and 60 MoA traces. Provider/model mismatches were zero. All 60 aggregator outputs were non-empty and matched persisted final-answer hashes.

## Reference-output audit

| Reference model | Calls | Substantive | `(empty response)` | Standalone mean | Perfect | Partial | Zero | Trace cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MiniMax M3 | 30 | 27 | 3 | 0.6164 | 14 | 11 | 5 | $0.15184188 |
| MiMo V2.5 | 30 | 24 | 6 | 0.6184 | 14 | 8 | 8 | $0.0392233016 |

The standalone score applies the same deterministic LiveBench processors directly to reference advice. It is diagnostic: the reference system prompt asks for advice to an aggregator, not necessarily a final format-compliant answer.

Every `(empty response)` trace showed the same exhaustion pattern:

- `output_tokens: 10000`
- `reasoning_tokens: 9999`
- visible output replaced by Hermes with `(empty response)`

These were real billed calls, but they supplied no visible reference advice. Treating them as valid would overstate the MoA treatment.

### Aggregator behavior relative to references

| Treatment | Improved | Unchanged | Regressed | Zero reference → perfect final |
|---|---:|---:|---:|---:|
| `moa_minimax` | 14 | 16 | 0 | 5 |
| `moa_mimo` | 12 | 18 | 0 | 5 |

For MiMo, two zero-scoring reasoning references remained zero after aggregation. The aggregator otherwise frequently corrected partial, wrong, or absent reference advice.

## Exploratory final scores — invalid evidence

These values describe completed final outputs, but must not be used as a valid treatment comparison because the reference contract failed.

| Arm | Mean | Absolute delta vs base | Relative delta |
|---|---:|---:|---:|
| `base` | 0.6861 | — | — |
| `moa_minimax` | 0.8483 | +0.1622 | +23.64% |
| `moa_mimo` | 0.7983 | +0.1122 | +16.35% |

Category means:

| Arm | Instruction Following | Reasoning | Data Analysis |
|---|---:|---:|---:|
| `base` | 0.5883 | 0.7700 | 0.7000 |
| `moa_minimax` | 0.7450 | 1.0000 | 0.8000 |
| `moa_mimo` | 0.7950 | 0.8000 | 0.8000 |

Direct MiMo-versus-MiniMax comparison:

- sample wins / ties / losses: `3 / 23 / 4`
- task wins / ties / losses: `3 / 9 / 3`
- MiMo mean delta: `-0.0500`

With only two samples per task and invalid reference delivery, no superiority conclusion is warranted.

## Harness defect and correction

The old validator rejected blank strings but accepted the literal Hermes fallback sentinel. The correction:

1. rejects normalized `(empty response)` as degraded reference evidence;
2. revalidates all persisted MoA traces whenever `score` runs, rather than trusting an older trace-audit file;
3. adds regression tests for both contracts.

Verification after the fix:

- 41 tests passed;
- Ruff formatting/check passed;
- `git diff --check` passed;
- deterministic rescore of this run exited 1 on degraded reference evidence.

## Next valid experiment

Do not rerun unchanged settings. First prevent reference reasoning from consuming the entire visible-output budget—for example with a model-appropriate reasoning/output configuration or a larger verified reference limit—then run a small targeted preflight that proves both reference models return substantive visible outputs before repeating the 15×2 paid matrix.
