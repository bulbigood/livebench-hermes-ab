# LiveBench Hermes multi-arm harness

This repository runs a frozen two-arm Hermes experiment using a typed, schema-versioned harness. The production default contains 15 scenarios, 10 samples per scenario, and two arms: 300 cells and at most 450 provider calls. The active arms are `base` and `moa_mimo`. The cohort uses a separately scored one-sample selection pilot and retains one CTA scenario as an explicit floor/identifiability control.

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

`--full` is deliberately explicit. For the current config it changes the run from 1 to 10 samples per scenario and from 30 to 300 cells. The configured MoA topology raises the maximum provider-call count to 450. To use another production sample count, change `generation.samples_per_task` in `config.yaml` before preparing the run.

## Manual lifecycle

Use the canonical subcommands when preparation, execution, resume, and scoring must be controlled separately. Always prepare before any paid manual execution:

```bash
uv run livebench-hermes-ab --config config.yaml prepare --run-dir runs/default
```

`prepare` performs no model calls. It validates the strict v2 config, pinned upstream revision, selected questions, Hermes source, arm order, and planned call count, then atomically publishes a prepared directory. Hermes can be selected in exactly one of three modes:

```yaml
# Installed release from PATH
compatibility:
  hermes:
    release: 0.19.1

# Exact Git revision, checked out into the harness cache
compatibility:
  hermes:
    repository: https://github.com/NousResearch/hermes-agent.git
    commit: bfff32ae8c6a9c585431997a6cc3d791b6ec9af5

# Existing source/install directory; the path must be absolute
compatibility:
  hermes:
    directory: /opt/hermes-agent
```

Git and directory checkouts with `pyproject.toml` run through their own `uv run --project` environment; an existing `.venv/bin/hermes` or executable `hermes` launcher is used as fallback. `--hermes-executable` remains an explicit operator override, mainly for fixtures and diagnostics.

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

To extend a completed frozen cohort without rerunning or replacing its existing
observations, create a new run from the old one and then resume only the newly
planned sample indices:

```bash
uv run livebench-hermes-ab extend \
  --run-dir runs/default-10 \
  --output-run-dir runs/default-20 \
  --to-samples 20
uv run livebench-hermes-ab resume --run-dir runs/default-20
```

`extend` requires an exact old-manifest subset, verifies copied cell and attempt
digests, and records provenance in `extension.json`. Planned direct arm contrasts
may be frozen in YAML as `scoring.contrasts: [[candidate, control]]`. Scoring also
emits sanitised MoA mechanism evidence and an attempt-level billing summary. Missing
provider usage, billing, or generation IDs remain explicit completeness warnings;
they are never silently treated as zero-cost calls.

Cell outcomes are durable and reason-coded. A harness failure stops admission, drains active calls, preserves their terminal evidence, and does not publish the execution-complete marker. Scoring uses only the common valid pair intersection across every arm. Historical schema-v1 runs are immutable evidence and are rejected rather than reinterpreted.

See [configuration](docs/configuration.md), [technical reference](docs/technical-reference.md), the [v14 confirmatory protocol](docs/evals/confirmatory-v14.md), and the [schema documents](docs/schemas/manifest-v2.md).

## Evaluation results

- [Latest evaluation: self-review mechanism experiment, 15×20, 2026-08-14](docs/evals/results/2026-08-14-self-review-mechanism-15x20.md)
- [MoA critic/wrapper paid pilot, 15×20, 2026-08-14](docs/evals/results/2026-08-14-moa-prompt-pilot-15x20.md)
