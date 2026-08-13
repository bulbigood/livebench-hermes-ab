# LiveBench Hermes multi-arm harness

This repository runs a frozen two-arm Hermes experiment using a typed, schema-versioned harness. The full matrix contains 15 scenarios, 20 samples per scenario, and two arms: 600 cells and at most 900 provider calls. The active arms are `base` and `moa_mimo`. The v14 confirmatory cohort uses a separately scored one-sample selection pilot and retains one CTA scenario as an explicit floor/identifiability control.

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

`--full` is deliberately explicit. For the current config it changes the run from 1 to 20 samples per scenario and from 30 to 600 cells. The configured MoA topology raises the maximum provider-call count to 900.

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
`execution.workers` must be an explicit multiple of the arm count. With two arms,
4 workers run two complete arm waves concurrently; 5 workers fail before execution.

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

See [configuration](docs/configuration.md), [technical reference](docs/technical-reference.md), the [v14 confirmatory protocol](docs/evals/confirmatory-v14.md), and the [schema documents](docs/schemas/manifest-v2.md).

## Evaluation results

- [Latest evaluation: v13 selection cohort, 2026-08-13](docs/evals/results/2026-08-13-full-paid-v13-selection.md)
