# Technical reference

## Prepare lifecycle

```bash
uv run livebench-hermes-ab --config config.yaml --hermes-executable "$HERMES" prepare \
  --run-dir runs/example
```

`prepare` makes no provider/model calls. It:

1. validates the experiment and arm contracts;
2. verifies the pinned LiveBench submodule commit and release;
3. loads the local question corpus and resolves the shared scenarios;
4. validates credentials without recording them in the manifest;
5. creates isolated Hermes homes for every arm;
6. identifies the selected Hermes binary and either runs strict profile probes or records a version-mismatch warning;
7. freezes scenario, config, question, arm-home, and execution hashes;
8. writes `manifest.json` and `questions.json`.

Inspect at least:

- `task_count`, `samples_per_task`, and `paired_units`;
- `expected_model_calls.by_arm` and `expected_model_calls.total`;
- `selection.scenarios`, category/family counts, and `scenarios_sha256`;
- `execution_contract`;
- `home_config_sha256`;
- `hermes_compatibility.status`, version, profile, warnings, and per-arm effective settings when verified.

`prepare` is fail-closed for missing binaries, invalid experiment/configuration data, credential errors, and failed probes on the exact verified Hermes profile. A version mismatch alone is warning-only: version-specific probes are skipped and execution remains allowed.

A fresh run directory is required. Runtime directories are created with restrictive permissions and ignored by Git.

## Execution model

```bash
uv run livebench-hermes-ab --config config.yaml --hermes-executable "$HERMES" run \
  --run-dir runs/example
```

The default `streaming` mode submits the complete arm-cell matrix to a bounded worker pool. A free worker immediately starts the next cell; slow arms do not hold idle slots behind a pair barrier. Automatic concurrency is `min(CPU count × 4, 32)` and may be overridden with `--workers 1..32`.

Each worker atomically persists a terminal outcome before returning. Valid outcomes contain the original answer record. Excluded outcomes contain the frozen cell identity plus a reason code and diagnostic. Consolidation writes deterministic per-arm JSONL and `exclusions.json`; a later cell failure cannot erase earlier paid results.

Scoring validates every persisted cell independently. Arm-local descriptive coverage may differ, but paired aggregates use only the common valid intersection across all configured arms. Any missing cell without a declared exclusion is a contract error. Run-level integrity failures are never downgraded to exclusions.

Hermes 0.19.1 MoA traces contain usage and final trace timestamps, but no reference-call start, completion, or duration fields. Consequently, full MoA cell timing is reported separately and marked as non-reference-phase timing.

For synchronized timing, pass `--balanced-waves`. Each wave contains as many complete counterbalanced arm groups as fit in the worker budget, starts them behind an explicit barrier, and waits for the complete wave before continuing:

```text
wave 1: cell 1 [arm-a || arm-b || arm-c]
        cell 2 [arm-b || arm-c || arm-a]
        --------------- barrier ---------------
wave 2: cell 3 [arm-c || arm-a || arm-b]
```

Properties:

- streaming permits multiple active cells per arm in isolated homes;
- balanced waves never split a complete arm group across waves;
- arm order rotates deterministically between pairs;
- thread identities need not persist between cells;
- Hermes subprocesses perform model work; Python workers mostly wait;
- MoA reference fanout may create additional provider-level concurrency inside one arm.

Parallelism is an execution condition, not a model treatment. It may affect latency, throttling, or provider scheduling.

Before each invocation, the runner verifies frozen config, selected questions, and generated Hermes config hashes. Every terminal cell outcome is written atomically before run-level consolidation. A timeout or known model/provider failure becomes a reason-coded cell exclusion; an unexpected harness exception still fails the run, while completed journals remain durable. Records and exclusions are consolidated in manifest order rather than concurrent completion order.

The absolute Hermes executable recorded during `prepare` is also used for every model call. This prevents probing one installation and accidentally executing another from `PATH`.

For diagnostics, one arm can be run sequentially:

```bash
uv run livebench-hermes-ab --config config.yaml --hermes-executable "$HERMES" run-arm \
  --arm moa --run-dir runs/moa-diagnostic
```

Do not combine independently generated diagnostic arms into a causal comparison unless prompts, cells, reference bytes, and execution conditions are identical.

## Isolation

Concurrent cells do not share writable Hermes homes. Each cell clones its arm's frozen template into `cell-homes/<arm>/<pair-id>/`; credentials remain allowlisted and local. Cells therefore do not share:

- `HERMES_HOME`;
- generated `config.yaml`;
- state/session databases;
- answer JSONL;
- MoA trace directories;
- credential allowlists.

Workers write unique atomic outcome journals rather than concurrently appending shared JSONL. The coordinator deterministically consolidates those journals after draining workers. Per-cell MoA traces are copied into the arm aggregate trace directory with pair-scoped names before validation.

`resume` validates the frozen journal schema, config and generated-home hashes, selected questions,
arm definitions, and the complete Hermes compatibility probe. It executes only cells without a
terminal outcome. `resume --retry-excluded` additionally retries only `CELL_TIMEOUT`,
`MODEL_OR_PROVIDER_FAILURE`, and locally invalid/degraded MoA traces. It archives previous attempts
before replacement and refuses runs created before durable cell journals were introduced.

## Output files

A completed run contains:

```text
runs/<run>/manifest.json
runs/<run>/questions.json
runs/<run>/homes/<arm>/config.yaml
runs/<run>/cell-homes/<arm>/<pair-id>/
runs/<run>/cells/<arm>/<pair-id>.json
runs/<run>/attempts/<arm>/<pair-id>/<attempt>-previous/
runs/<run>/exclusions.json
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

Scoring is local and deterministic. It uses pinned LiveBench objective processors and makes no judge-model calls. It revalidates persisted MoA traces before computing scores, so an older or stale trace audit cannot bypass the current validation contract.

Compatibility warnings are copied from `manifest.json` into `summary.json`. A complete run made with a mismatched Hermes version is labeled `VALID_WITH_HERMES_WARNING`; objective scores remain available, but the result is not presented as a verified reproduction.

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
- substantive reference outputs and positive output-token usage; the Hermes `(empty response)` sentinel is rejected as degraded evidence;
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

`run_makespan_seconds` is the elapsed duration of the complete execution. `sum_cell_seconds` is a sum of overlapping subprocess durations and is not wall time. Streaming summaries mark arm timing with `*` and set `paired_wall_time_comparable: false`; the note states that non-strict scheduling is not paired arm wall-time evidence. Balanced-wave timing has no marker. Quality scores are not automatically invalidated by the timing marker when exact coverage and provenance remain valid. Do not report USD cost unless provider prices and complete token telemetry are available.

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
