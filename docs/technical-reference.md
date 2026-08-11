# Technical reference

## Prepare lifecycle

```bash
uv run livebench-hermes-ab --config config.yaml prepare \
  --run-dir runs/example
```

`prepare` makes no provider/model calls. It:

1. validates the experiment and arm contracts;
2. verifies the pinned LiveBench submodule commit and release;
3. loads the local question corpus and resolves the shared scenarios;
4. validates credentials without recording them in the manifest;
5. creates isolated Hermes homes for every arm;
6. runs offline, fail-closed Hermes compatibility probes;
7. freezes scenario, config, question, arm-home, and execution hashes;
8. writes `manifest.json` and `questions.json`.

Inspect at least:

- `task_count`, `samples_per_task`, and `paired_units`;
- `expected_model_calls.by_arm` and `expected_model_calls.total`;
- `selection.scenarios`, category/family counts, and `scenarios_sha256`;
- `execution_contract`;
- `home_config_sha256`;
- `hermes_compatibility.version`, profile, and per-arm effective settings.

A fresh run directory is required. Runtime directories are created with restrictive permissions and ignored by Git.

## Execution model

```bash
uv run livebench-hermes-ab --config config.yaml run \
  --run-dir runs/example
```

The default `paired_arms` mode executes one cell across all arms concurrently, then waits at a barrier:

```text
cell 1: arm-a || arm-b || arm-c
        -------- barrier --------
cell 2: arm-a || arm-b || arm-c
```

Properties:

- maximum one active cell per arm;
- up to one harness worker per arm for the current cell;
- the next cell waits for the slowest arm;
- thread identities need not persist between cells;
- Hermes subprocesses perform model work; Python workers mostly wait;
- MoA reference fanout may create additional provider-level concurrency inside one arm.

Parallelism is an execution condition, not a model treatment. It may affect latency, throttling, or provider scheduling.

Before each invocation, the runner verifies frozen config, selected questions, and generated Hermes config hashes. Non-empty answer files are rejected rather than overwritten. A failed arm fails the current cell and run.

For diagnostics, one arm can be run sequentially:

```bash
uv run livebench-hermes-ab --config config.yaml run-arm \
  --arm moa --run-dir runs/moa-diagnostic
```

Do not combine independently generated diagnostic arms into a causal comparison unless prompts, cells, reference bytes, and execution conditions are identical.

## Isolation

Arms do not share:

- `HERMES_HOME`;
- generated `config.yaml`;
- state/session databases;
- answer JSONL;
- MoA trace directories;
- credential allowlists.

The coordinator writes answer JSONL after joining a paired wave, so workers do not concurrently append to the same file.

## Output files

A completed run contains:

```text
runs/<run>/manifest.json
runs/<run>/questions.json
runs/<run>/homes/<arm>/config.yaml
runs/<run>/raw/hermes-<arm>.jsonl
runs/<run>/scores.json
runs/<run>/paired-deltas.json
runs/<run>/summary.json
runs/<run>/trace-audit.json
runs/<run>/trace-audit-<additional-moa-arm>.json
```

Runtime files under `runs/` are ignored by Git and may include credentials or provider output. Do not publish the run directory without a separate privacy review.

## Scoring

```bash
uv run livebench-hermes-ab --config config.yaml score \
  --run-dir runs/example
```

Scoring is local and deterministic. It uses pinned LiveBench objective processors and makes no judge-model calls.

Coverage is compared on the exact common `(question_id, sample_index)` intersection. Unless an explicitly supported amendment applies, incomplete coverage is invalid.

Category means are computed as:

1. score each sample;
2. average samples within each task;
3. average tasks within each category.

For every non-baseline arm:

```text
absolute delta = arm mean - baseline mean
relative delta = (arm mean - baseline mean) / baseline mean × 100%
```

Relative delta is `null`/`N/A` when the baseline mean is zero. Absolute delta is always reported.

`summary.json` includes:

- mean score for every arm;
- absolute and relative delta against `execution.baseline_arm`;
- task-balanced mean delta;
- wins, ties, and regressions on common cells;
- category means for every arm.

## MoA trace validation

Every configured MoA arm with reference models is validated independently. Validation requires:

- one trace per completed cell;
- expected preset and reference cardinality;
- exact reference provider/model identities;
- non-empty reference outputs and positive output-token usage;
- exact aggregator provider/model identity;
- aggregator output hashes matching persisted answers.

`degraded_reference_policy: loud` is recommended. Missing or silently degraded reference evidence is not accepted as a valid MoA treatment.

## Manifest and reproducibility

The manifest freezes:

- source config hash;
- pinned upstream commit;
- question-file hashes;
- resolved scenario order and hash;
- selected question hash;
- generated per-arm Hermes config hashes;
- Hermes compatibility evidence;
- samples, retries, timeout, baseline, concurrency, and call-count scope.

It cannot freeze:

- provider behavior;
- mutable model revisions behind provider aliases;
- network conditions;
- quotas and throttling;
- pricing.

Report wall-clock makespan separately from summed/per-cell latency. Do not report USD cost unless provider prices and complete token telemetry are available.

## Security boundaries

Tracked configuration stores credential names only. The repository ignores:

- `runs/`;
- `data/`;
- `.env` and `.env.*` except `.env.example`;
- `auth.json`;
- state/session/log files;
- private-key formats;
- build and virtual-environment artifacts.

Inline credentials in Hermes config are rejected. OAuth state and generated arm `.env` files remain local runtime material. Provider prompts/results may also be private and belong under ignored run directories.

Before publishing changes, inspect both tracked files and Git history. Gitleaks is recommended:

```bash
gitleaks detect --source . --redact --no-banner
```

## Development verification

```bash
uv run pytest -q
uv run ruff format --check src tests
uv run ruff check src tests scripts
uv build
git diff --check
gitleaks detect --source . --redact --no-banner
```

A no-cost live preflight is:

```bash
uv run livebench-hermes-ab --config config.yaml prepare \
  --run-dir runs/publication-preflight
```

Remove generated preflight credentials/runtime after auditing if the run will not be used.

## Repository layout

- `config.yaml`: supported public multi-arm configuration;
- `config/`: immutable historical experiment contracts;
- `docs/`: user and technical documentation;
- `reports/`: historical benchmark evidence and scenario rationale;
- `src/livebench_hermes_ab/`: runner, scoring, and trace validation;
- `tests/`: deterministic contract tests;
- `upstream/`: pinned LiveBench Git submodule;
- `data/`: ignored downloaded corpus;
- `runs/`: ignored runtime and results.
