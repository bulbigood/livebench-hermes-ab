# LiveBench Hermes multi-arm harness

This repository runs a frozen three-arm Hermes experiment using a typed, schema-versioned harness. The default matrix contains 15 scenarios, ten samples per scenario, and three arms: 450 cells and at most 600 provider calls. The active arms are `base`, `gpt_medium`, and `moa_mimo`; `moa_minimax` was removed after its reliability deficit in the v10 evaluation. The current hard cohort uses output-blind selections from deterministic instruction-following, mathematics, language, and data-analysis families.

## Safe default run

> **Warning:** execution starts many provider calls concurrently. With `execution.workers: auto`, the harness uses five workers per detected CPU, capped at 40. A run can consume API tokens and rate limits very quickly. Before a full evaluation, run the one-sample default pipeline and verify every configured model, MoA reference model, token limit, provider credential, account budget, and API rate limit.

Running the command without a subcommand executes the complete `prepare → run → score` pipeline with **one sample per scenario**, regardless of the larger sample count stored in `config.yaml`:

```bash
uv run livebench-hermes-ab
```

The output is written to a timestamped `runs/smoke-<UTC timestamp>` directory. Use `--run-dir` to choose another destination or `--credentials-file` to select a dotenv source.

Only after the smoke run succeeds and the provider configuration has been checked should you opt into the sample count from the config:

```bash
uv run livebench-hermes-ab --full
```

`--full` is deliberately explicit. For the current config it changes the run from 1 to 10 samples per scenario and from 45 to 450 cells. The configured MoA topology raises the maximum provider-call count to 600.

## Manual lifecycle

Use the canonical subcommands when preparation, execution, resume, and scoring must be controlled separately. Always prepare before any paid manual execution:

```bash
uv run livebench-hermes-ab --config config.yaml prepare --run-dir runs/default
```

`prepare` performs no model calls. It validates the strict v2 config, pinned upstream revision, selected questions, Hermes version, arm order, and planned call count, then atomically publishes a prepared directory.

Credential values never belong in the experiment YAML. `prepare` resolves only the variable
names allowlisted by each arm's `credential_env`. It first checks the environment inherited by
the harness process, then a dotenv credentials file. The portable default is
`$HERMES_HOME/.env`; an explicit secret source can be selected without recording its path or
contents in run evidence:

```bash
uv run livebench-hermes-ab --config config.yaml prepare \
  --credentials-file "$HOME/.config/livebench-hermes/credentials.env" \
  --run-dir runs/default
```

Samples and scheduling mode are frozen in `config.snapshot.yaml` and `manifest.json`. The default pipeline safely overrides `generation.samples_per_task` to one in its frozen snapshot; `--full` preserves the configured value. Worker count remains controlled by `execution.workers`. `auto` resolves to five workers per detected CPU with a hard maximum of 40. In `balanced_waves` mode,
`execution.workers` must be an explicit multiple of the arm count. With three arms,
6 workers run two complete arm waves concurrently; 7 workers fail before execution.

Execution and scoring are deliberately separate:

```bash
# Paid: invokes configured providers.
uv run livebench-hermes-ab --config config.yaml run --run-dir runs/default

# Paid only when cells remain eligible for retry.
uv run livebench-hermes-ab --config config.yaml resume --run-dir runs/default

# Deterministic: never invokes providers or changes cell journals.
uv run livebench-hermes-ab --config config.yaml score --run-dir runs/default
```

Cell outcomes are durable and reason-coded. A harness failure stops admission, drains active calls, preserves their terminal evidence, and does not publish the execution-complete marker. Scoring uses only the common valid pair intersection across every arm. Historical schema-v1 runs are immutable evidence and are rejected rather than reinterpreted.

See [configuration](docs/configuration.md), [technical reference](docs/technical-reference.md), and the [schema documents](docs/schemas/manifest-v2.md).

## Evaluation results

### Hard cohort v10 — 2026-08-13

The completed paid run executed **600/600 cells**. Primary scoring used **119/150 common-valid pairs (79.33%)**:

| Rank | Arm | Mean | Delta vs `base` |
|---:|---|---:|---:|
| 1 | `moa_minimax` | **0.9494** | +0.0276 |
| 2 | `moa_mimo` | **0.9489** | +0.0271 |
| 3 | `gpt_medium` | **0.9256** | +0.0038 |
| 4 | `base` | **0.9218** | — |

`moa_minimax` led `moa_mimo` by only **0.0005**. All paired 95% confidence intervals for improvements over `base` crossed zero, so the run ranks the arms but does not establish confirmatory superiority. Reliability also differed materially: 31 pairs were excluded due to 26 invalid MoA traces and 5 timeouts; 27 excluded cells belonged to `moa_minimax`, 4 to `moa_mimo`, and none to the non-MoA arms. Six of the 15 scenarios remained fully saturated.

See the [full hard-cohort v10 report](docs/evals/results/2026-08-13-hard-cohort-v10.md) for scenario-level scores, category results, exclusions, trace-token totals, confidence intervals, and comparison with v9.
