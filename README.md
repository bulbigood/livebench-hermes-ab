# LiveBench Hermes multi-arm harness

This repository runs a frozen four-arm Hermes experiment using a typed, schema-versioned harness. The default matrix contains 15 questions, five samples, and four arms: 300 cells and 450 provider calls.

Always prepare before any paid execution:

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

Samples, scheduling mode, and worker count are configured only in `config.yaml` and
frozen in `config.snapshot.yaml` and `manifest.json`. In `balanced_waves` mode,
`execution.workers` must be an explicit multiple of the arm count. With four arms,
8 workers run two complete arm waves concurrently; 7 workers fail before execution.

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

- [2026-08-13 full paid run](docs/evals/results/2026-08-13-full-paid.md) — 600 cells, 139/150 common-valid pairs; `moa_mimo` achieved the highest mean score at 0.9285.
