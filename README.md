# LiveBench Hermes multi-arm harness

Compare multiple [Hermes Agent](https://hermes-agent.nousresearch.com/) configurations on exactly the same LiveBench scenarios.

The default experiment compares:

- `base`: plain Hermes using OpenAI Codex;
- `moa_minimax`: the same aggregator plus `minimax/minimax-m3` through OpenRouter;
- `moa_mimo`: the same aggregator plus `xiaomi/mimo-v2.5` through OpenRouter.

It runs 15 tasks × 5 samples = **75 cells per arm**. The three arms produce **225 arm-cell invocations**. Including one reference call for each MoA cell, the default configuration expects **375 provider model calls in total**. Model calls may cost money.

> **Safe rule:** always run `prepare` first. It makes no model calls and prints the exact planned call count. Run `run` only after checking that output.

## Run the default benchmark

### 1. Install the required tools

You need:

- Linux or macOS;
- Git;
- Python 3.11+;
- [`uv`](https://docs.astral.sh/uv/).

### 2. Clone and install this project

```bash
git clone --recurse-submodules https://github.com/bulbigood/livebench-hermes-ab.git
cd livebench-hermes-ab
uv sync --extra livebench
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

Install the pinned project-local Hermes runtime. This does not replace a system Hermes or create a command in `~/.local/bin`:

```bash
./scripts/install-hermes-runtime.sh
HERMES="$PWD/.hermes-runtime/hermes-agent/.venv/bin/hermes"
"$HERMES" --version
```

The version should be `0.19.1`. The runtime directory is ignored by Git.

You may instead use an existing Hermes:

```bash
HERMES="$(command -v hermes)"
```

A different version is allowed, but every output is marked with a Hermes compatibility warning. It is not a verified reproduction and may still fail if that Hermes cannot execute the configured arms. See [Hermes compatibility](docs/configuration.md#hermes-version-compatibility).

### 3. Configure the two default providers

The default `base` arm uses your existing OpenAI Codex OAuth login:

```bash
"$HERMES" auth add openai-codex
```

The default `moa_minimax` and `moa_mimo` arms also need an OpenRouter API key:

```bash
export OPENROUTER_API_KEY='your-key-here'
```

Do **not** paste token values into `config.yaml`. The config contains only the allowed environment-variable name:

```yaml
credential_env:
  - OPENROUTER_API_KEY
```

See [Credentials](docs/configuration.md#credentials) for `.env` usage and isolation details.

### 4. Download the benchmark data

```bash
PYTHONPATH=upstream uv run --extra livebench python upstream/livebench/download_questions.py
```

Download the local scoring resources:

```bash
NLTK_DATA="$HOME/.cache/nltk_data" uv run --extra livebench python - <<'PY'
import nltk
nltk.download("punkt")
nltk.download("punkt_tab")
PY
```

The downloaded `data/` directory is ignored by Git.

### 5. Prepare the run — no model calls

Use a new run directory:

```bash
uv run livebench-hermes-ab --config config.yaml --hermes-executable "$HERMES" prepare \
  --run-dir runs/default
```

This validates credentials, scenarios, generated arm configs, concurrency, and the pinned LiveBench revision. With Hermes `0.19.1`, it also verifies effective provider/model/reasoning/MoA settings. With another version, it records a prominent unverified-version warning instead. It then writes `runs/default/manifest.json`.

Print the planned call count:

```bash
uv run python - <<'PY'
import json
manifest = json.load(open("runs/default/manifest.json"))
print(json.dumps(manifest["expected_model_calls"], indent=2))
PY
```

For the unchanged default config, `expected_cells` should be `225` and `expected_model_calls.total` should be `375`. Stop here if the arms, scenarios, or call count are not what you intended.

### 6. Run the benchmark — this makes model calls

```bash
uv run livebench-hermes-ab --config config.yaml --hermes-executable "$HERMES" run \
  --run-dir runs/default
```

Do not edit `config.yaml` after `prepare`. The runner rejects config drift.

### 7. Score the completed run

```bash
uv run livebench-hermes-ab --config config.yaml score \
  --run-dir runs/default
```

The command prints the summary and writes:

```text
runs/default/summary.json
runs/default/scores.json
runs/default/paired-deltas.json
runs/default/trace-audit.json
```

To start over, use a different run directory such as `runs/default-2`. Existing answer files are intentionally not overwritten.

## Configure your own arms

Start from a copy so the public example remains intact:

```bash
cp config.yaml my-experiment.yaml
```

### 1. Give the experiment a new ID

```yaml
experiment:
  id: my-model-comparison-v1
```

### 2. Define the baseline

Every other arm is compared with this arm:

```yaml
execution:
  baseline_arm: control
```

### 3. Add complete arm blocks

Each `arms.<name>.hermes` block is a complete Hermes config. Nothing is inherited from the baseline.

A minimal plain arm looks like this:

```yaml
arms:
  control:
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

To add another plain arm, copy the whole block and change the arm name and Hermes settings:

```yaml
  candidate-high:
    credential_env: []
    hermes:
      model:
        provider: openai-codex
        default: gpt-5.6-sol
      agent:
        reasoning_effort: high
        disabled_toolsets: [web, browser, terminal, file, memory]
      moa:
        enabled: false
        save_traces: false
```

For an API-key provider, list only the environment-variable name:

```yaml
  openrouter-candidate:
    credential_env:
      - OPENROUTER_API_KEY
    hermes:
      model:
        provider: openrouter
        default: vendor/model-name
      agent:
        reasoning_effort: medium
      moa:
        enabled: false
        save_traces: false
```

Then export the value before `prepare` and `run`:

```bash
export OPENROUTER_API_KEY='your-key-here'
```

For MoA arms, reference models and aggregator settings live inside that arm's `hermes.moa` tree. Use the complete `moa_minimax` or `moa_mimo` block in [`config.yaml`](config.yaml) as the template. See [Arm configuration](docs/configuration.md#arms) for the full contract.

### 4. Choose the shared scenarios

Scenarios are configured once and used by **every** arm:

```yaml
selection:
  scenarios:
    reasoning:
      - id: "<LiveBench question_id>"
        family: zebra_puzzle
        note: "optional note"
    data_analysis:
      - id: "<LiveBench question_id>"
        family: tablejoin
```

`id` selects the local pinned LiveBench record. The category and `family` are checked during `prepare`. Optional `source_url` and `note` fields are metadata only.

See [Scenario selection](docs/configuration.md#shared-scenarios) for validation rules and how IDs are frozen in the manifest.

### 5. Prepare before spending money

```bash
uv run livebench-hermes-ab --config my-experiment.yaml --hermes-executable "$HERMES" prepare \
  --run-dir runs/my-experiment
```

Check `expected_model_calls`, `selection`, and `hermes_compatibility` in the printed manifest. If they are correct:

```bash
uv run livebench-hermes-ab --config my-experiment.yaml --hermes-executable "$HERMES" run \
  --run-dir runs/my-experiment

uv run livebench-hermes-ab --config my-experiment.yaml score \
  --run-dir runs/my-experiment
```

## Common errors

| Error | What to do |
|---|---|
| `Hermes version mismatch` warning | The run is allowed, but its manifest and summary are marked unverified. Use `./scripts/install-hermes-runtime.sh` for the verified version. |
| explicit Hermes executable is missing | Set `HERMES` to an executable file, or rerun the project-local installer. No fallback occurs after an explicit path is supplied. |
| `OPENROUTER_API_KEY is missing` | Export it in the same shell before `prepare` and `run`. |
| `no LiveBench question.jsonl files found` | Run the download command from step 4. |
| `selected scenario IDs unavailable` | Use IDs present in the pinned local LiveBench release. |
| config or question drift | Delete the incomplete run directory or choose a new one, then run `prepare` again. |
| answer file already contains data | Use a new run directory. The harness does not overwrite model output. |

## Documentation

- [Configuration: arms, scenarios, credentials, compatibility](docs/configuration.md)
- [Technical reference: execution, manifests, scoring, traces, reproducibility](docs/technical-reference.md)
- [Default scenario-selection rationale](reports/targeted-moa-scenario-selection.md)
- [Hermes Agent configuration reference](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/)

## License

Harness code is released under the [MIT License](LICENSE). LiveBench and downloaded benchmark data retain their upstream licenses and terms.
