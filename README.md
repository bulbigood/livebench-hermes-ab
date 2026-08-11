# LiveBench Hermes multi-arm harness

Reproducible, objective LiveBench comparisons for independently configured [Hermes Agent](https://hermes-agent.nousresearch.com/) arms.

The default experiment compares a plain Hermes arm with a Mixture-of-Agents (MoA) arm on a frozen 15-task cohort:

- 5 Instruction Following tasks;
- 5 Reasoning tasks;
- 5 Data Analysis tasks;
- 5 stochastic samples per task;
- 75 cells per arm.

LiveBench is pinned as a Git submodule at commit `00eae856aa1c1a9e9d058a65a9a94d85884034c4`. Historical YAML contracts and reports remain in `config/` and `reports/`; `config.yaml` is the supported user-facing configuration.

## Execution model

Every configured arm gets:

- one sequential worker;
- an isolated local `HERMES_HOME`;
- its own `config.yaml`, `.env`, state, sessions, MoA traces, and answer JSONL.

All arms for one `(question_id, sample_index)` run concurrently. The next cell starts only after every arm finishes. This keeps cells within an arm sequential while aligning competing arms in time. Adding a third arm creates a third worker; it does not add within-arm concurrency.

Model calls can cost money. `prepare` is deterministic and makes no model calls. Always inspect its `expected_model_calls` output before `run`.

## Requirements

- Linux or macOS;
- Python 3.11+;
- [`uv`](https://docs.astral.sh/uv/);
- Git with submodule support;
- Hermes Agent installed and ...[truncated]

Verify the local tools:

```bash
hermes --version
hermes config check
uv --version
```

Clone and install:

```bash
git clone --recurse-submodules <repository-url>
cd livebench-hermes-ab
uv sync --extra test --extra livebench
```

If the repository was cloned without submodules:

```bash
git submodule update --init --recursive
```

Download the public LiveBench questions and NLTK resources:

```bash
PYTHONPATH=upstream uv run --extra livebench python upstream/livebench/download_questions.py
NLTK_DATA="$HOME/.cache/nltk_data" uv run --extra livebench python - <<'PY'
import nltk
nltk.download("punkt")
nltk.download("punkt_tab")
PY
```

`data/` and `runs/` are ignored by Git.

## Configure Hermes arms

The root [`config.yaml`](config.yaml) has two layers.

### Harness-owned sections

- `experiment`: immutable experiment identity, upstream revision, release, seed, and question paths.
- `selection`: one exact experiment-global scenario list shared by every arm.
- `generation`: samples, retries, and per-Hermes-process timeout.
- `execution`: baseline arm and concurrency policy.
- `scoring`: local objective scorer declaration.
- `arms.<name>.credential_env`: names of environment variables allowed in that arm.

### Configure the shared scenarios

Declare scenarios once under category-grouped YAML bullet lists:

```yaml
selection:
  scenarios:
    reasoning:
      - id: "<LiveBench question_id>"
        family: zebra_puzzle
        source_url: "https://example.org/provenance"  # optional
        note: "level 20"                              # optional
    coding:
      - id: "<LiveBench question_id>"
        family: code_generation
    data_analysis:
      - id: "<LiveBench question_id>"
        family: tablejoin
```

The section key is the expected LiveBench `category`. `family` is the expected LiveBench `task`. Both are checked against the local corpus pinned by `experiment.upstream_commit` and `experiment.release`; they are not decorative labels. Category names are not hard-coded, so `coding`, `math`, or another LiveBench category works when the selected IDs are present and active in that pinned corpus.

`id` is the only executable selector. `source_url` and `note` are optional provenance metadata stored in the manifest; URLs are never fetched during `prepare`, execution, or scoring. This avoids turning an external website into an accidental benchmark dependency.

The grouped list is resolved once before any arm runs. Duplicate IDs, unavailable or retired IDs, unsupported item keys, malformed URLs, and category/family mismatches fail `prepare`. Arm-local scenario overrides do not exist, so every arm receives the same frozen `(question_id, sample_index)` matrix.

The manifest preserves the configured scenario order under `selection.scenarios`, records derived category/family counts, and stores `selection.scenarios_sha256`. Pair execution order is separately shuffled from the experiment seed. Legacy immutable configs using a flat `selection.question_ids` list remain supported, but a config cannot define both forms.

### Hermes-owned section

`arms.<name>.hermes` is an ordinary Hermes YAML configuration tree. The harness serializes this tree directly to:

```text
runs/<run>/homes/<name>/config.yaml
```

It does not rename model, reasoning, MoA, or provider fields and does not apply hidden model overrides. Generated semantic YAML is tested against the source subtree for exact equality.

Example plain arm:

```yaml
arms:
  base:
    credential_env: []
    hermes:
      model:
        provider: openai-codex
        default: gpt-5.6-sol
      agent:
        reasoning_effort: medium
        disabled_toolsets: [web, browser, terminal, file, memory]
      moa:
        enabled: false
        save_traces: false
```

Example MoA arm:

```yaml
  moa:
    credential_env: [OPENROUTER_API_KEY]
    hermes:
      model:
        provider: moa
        default: default
      agent:
        reasoning_effort: medium
      moa:
        enabled: true
        default_preset: default
        active_preset: default
        save_traces: true
        presets:
          default:
            enabled: true
            degraded_reference_policy: loud
            fanout: every_n:3
            reference_models:
              - provider: openrouter
                model: minimax/minimax-m3
            aggregator:
              provider: openai-codex
              model: gpt-5.6-sol
              reasoning_effort: medium
```

Consult the current [Hermes configuration reference](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/) when changing keys.

### Hermes version and schema compatibility

The public config selects a code-owned compatibility pro...[truncated]
### Add another arm

Copy any `arms.<name>` block and give it a unique alphanumeric, hyphenated, or underscored name. For example, duplicate `moa` as `moa-low`, then change only:

```yaml
arms:
  moa-low:
    credential_env: [OPENROUTER_API_KEY]
    hermes:
      agent:
        reasoning_effort: low
      # Copy the complete moa tree and set its aggregator reasoning_effort to low.
```

The complete Hermes subtree is required; YAML inheritance or an implicit BASE merge is deliberately not provided. Explicit configs are repetitive, but reproducible repetition beats an invisible treatment.

Set `execution.baseline_arm` to the arm against which all other arms are reported. `execution.workers_per_arm` must remain `1`.

## Credentials

Never put credential values in `config.yaml`.

The harness rejects non-empty inline credential fields such as `api_key`, `access_token`, `password`, `clie...[truncated]

- OAuth-backed providers use the existing `auth.json` from `--source-hermes-home` (default: `~/.hermes`). Generated homes receive a symlink to that file.
- API-key arms list only required variable names in `credential_env`.
- Values are resolved from the process environment, the source Hermes `.env`, or `/etc/environment`.
- Each generated arm `.env` contains only its allowlisted variables and has mode `0600`.
- Hermes child processes have inherited key/token/secret/password variables removed before the arm-specific `.env` is loaded.
- A missing allowlisted credential fails during `prepare`.

Examples:

```bash
export OPENROUTER_API_KEY='...'
hermes auth add openai-codex
```

A project-local `.env` is Git-ignored as a safety net but is not parsed implicitly. If you choose to use one, export it into the process environment before `prepare`/`run`:

```bash
set -a
. ./.env
set +a
```

The default BASE arm gets no API-key environment variables. Static LiveBench prompts do not need tools, so the default Hermes configs disable all bundled toolsets and execution uses `--ignore-rules`.

## Prepare and audit

Use a fresh run directory:

```bash
uv run livebench-hermes-ab --config config.yaml prepare \
  --run-dir runs/targeted-15x5
```

Inspect at least:

- `task_count`, `samples_per_task`, and `paired_units`;
- `expected_model_calls.by_arm` and `expected_model_calls.total`;
- `execution_contract`;
- `home_config_sha256`;
- `hermes_compatibility.version`, `profile`, and per-arm `effective` values;
- `selection.scenarios`, `scenarios_sha256`, and derived category/family counts.

The default config prepares 75 BASE calls, 75 MoA aggregator calls, and 75 reference calls: 225 model calls total and zero judge calls.

Verify a generated Hermes home without making a model call:

```bash
HERMES_HOME="$PWD/runs/targeted-15x5/homes/base" hermes config get model.provider
HERMES_HOME="$PWD/runs/targeted-15x5/homes/moa" hermes config get moa.active_preset
```

`prepare` runs all Hermes compatibility probes before any benchmark generation. It fails closed on an unsupported Hermes version, an unknown treatment-critical key, invalid types, effective provider/model/reasoning/MoA drift, a failed offline Hermes config load, upstream drift, unavailable question IDs, category/family cardinality changes, missing credentials, invalid arm names, or invalid worker counts.

Successful evidence is recorded in `manifest.json` under `hermes_compatibility`, including the executable, version line, profile, per-arm effective settings, config-check result, prompt-size digest, and tool-schema count. These probes are offline and make no provider calls.

## Run

```bash
uv run livebench-hermes-ab --config config.yaml run \
  --run-dir runs/targeted-15x5
```

The runner rejects non-empty answer files. It verifies the frozen config, selected questions, and generated Hermes configs before every cell. A failed arm fails the cell and the run; completed data remains available for diagnosis but cannot be scored as complete unless an explicitly supported amendment applies.

For diagnostics, one configured arm can be run sequentially:

```bash
uv run livebench-hermes-ab --config config.yaml run-arm \
  --arm moa --run-dir runs/moa-diagnostic
```

Do not combine independently generated diagnostic arms into a causal comparison unless prompts, cells, reference bytes, and execution conditions match.

## Score

```bash
uv run livebench-hermes-ab --config config.yaml score \
  --run-dir runs/targeted-15x5
```

Scoring is local and deterministic. It uses the pinned LiveBench objective processors and no judge-model calls.

Outputs include:

```text
runs/targeted-15x5/manifest.json
runs/targeted-15x5/questions.json
runs/targeted-15x5/raw/hermes-<arm>.jsonl
runs/targeted-15x5/scores.json
runs/targeted-15x5/paired-deltas.json
runs/targeted-15x5/summary.json
runs/targeted-15x5/trace-audit.json
runs/targeted-15x5/trace-audit-<additional-moa-arm>.json
```

`summary.json` reports:

- mean score for every arm;
- absolute and relative delta against `baseline_arm`;
- task-balanced mean delta;
- wins, ties, and regressions on the common cell intersection;
- category means for every arm.

Relative improvement is `N/A` (`null` in JSON) when the baseline mean is zero.

## MoA trace validation

Every arm whose active Hermes MoA preset has reference models is validated independently. Validation requires:

- one trace per completed benchmark cell;
- the configured preset and reference cardinality;
- exact reference provider/model identities;
- non-empty reference outputs and positive output-token usage;
- exact aggregator provider/model identity;
- aggregator output hashes matching persisted answers.

`degraded_reference_policy: loud` is recommended. A fallback without valid reference evidence is not silently accepted.

## Reproducibility boundaries

The manifest freezes source/config/question hashes and model-call scope. It cannot freeze external provider behavior, model revisions behind mutable names, network conditions, quotas, or pricing.

Parallel execution is an execution condition, not a model treatment. Concurrent arms may change latency and throttling compared with historical sequential runs. Report wall-clock makespan separately from summed and per-cell latency.

Do not report USD cost unless provider prices and complete token telemetry are available. Historical OpenAI Codex responses may not expose complete token accounting.

## Development and verification

```bash
uv run pytest -q
uv run ruff check src tests scripts
uv build
git diff --check
gitleaks detect --source . --redact --no-banner
```

The Gitleaks command scans Git history. Install Gitleaks separately if it is not already available. Before publishing, also verify that `git ls-files` contains no `.env`, `auth.json`, session database, request dump, private key, or credentials file.

A no-cost publication preflight is:

```bash
rm -rf runs/publication-preflight
uv run livebench-hermes-ab --config config.yaml prepare \
  --run-dir runs/publication-preflight
```

## Repository contents

- `config.yaml`: supported multi-arm configuration.
- `config/`: immutable historical experiment contracts.
- `reports/`: historical evidence and targeted scenario-selection rationale.
- `src/livebench_hermes_ab/`: runner, scoring, and trace validation.
- `tests/`: deterministic contract tests.
- `upstream/`: pinned LiveBench submodule.

## License

The harness code is released under the [MIT License](LICENSE). The pinned LiveBench submodule and downloaded benchmark data retain their own upstream licenses and terms.
