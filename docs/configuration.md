# Configuration reference

The supported user-facing configuration is the root [`config.yaml`](../config.yaml). Historical contracts under `config/` are retained for reproducibility and may use older schemas.

## Configuration layers

Harness-owned settings:

- `experiment`: experiment ID, pinned LiveBench commit/release, seed, and question paths;
- `selection`: one scenario set shared by all arms;
- `generation`: samples, retries, and process timeout;
- `execution`: baseline and concurrency policy;
- `compatibility`: verified Hermes profile and mismatch-warning policy;
- `scoring`: objective scoring declaration;
- `arms.<name>.credential_env`: credential names allowed for that arm.

Hermes-owned settings:

- `arms.<name>.hermes`: a complete Hermes YAML configuration tree.

The harness serializes each Hermes tree directly to:

```text
runs/<run>/homes/<arm>/config.yaml
```

It does not rename model, reasoning, MoA, or provider fields and does not apply hidden model overrides.

## Arms

Arm names may contain letters, numbers, hyphens, and underscores. Every arm requires:

```yaml
arms:
  arm-name:
    credential_env: []
    hermes:
      model: {}
      agent: {}
      moa: {}
```

`hermes` is complete, not a patch against the baseline. Explicit repetition prevents hidden treatment inheritance.

### Plain arm

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
        disabled_toolsets:
          - web
          - browser
          - terminal
          - file
          - memory
      moa:
        enabled: false
        save_traces: false
```

### MoA arm

```yaml
arms:
  moa:
    credential_env:
      - OPENROUTER_API_KEY
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
            reference_max_tokens: 30000
            max_tokens: 4096
            fanout: every_n:3
            reference_models:
              - provider: openrouter
                model: minimax/minimax-m3
            aggregator:
              provider: openai-codex
              model: gpt-5.6-sol
              reasoning_effort: medium
```

When changing MoA reasoning effort, inspect both `agent.reasoning_effort` and the active preset's `aggregator.reasoning_effort`. They are separate Hermes-native fields.

### Baseline and workers

```yaml
execution:
  parallelism: paired_arms
  workers_per_arm: 1
  baseline_arm: base
```

`baseline_arm` must name one configured arm. `workers_per_arm` must remain `1`: cells within an arm are sequential. Adding an arm adds one worker for the current paired wave.

## Shared scenarios

Scenarios are experiment-global:

```yaml
selection:
  scenarios:
    instruction_following:
      - id: "<question_id>"
        family: summarize
    reasoning:
      - id: "<question_id>"
        family: zebra_puzzle
        source_url: "https://example.org/provenance"
        note: "level 20"
    data_analysis:
      - id: "<question_id>"
        family: tablejoin
```

Fields:

- category section key: expected LiveBench `category`;
- `id`: required executable selector matching `question_id` in the local pinned corpus;
- `family`: required expected LiveBench `task`;
- `source_url`: optional HTTP(S) provenance metadata;
- `note`: optional metadata.

URLs are never fetched. The local pinned corpus is the only executable source.

`prepare` rejects:

- duplicate IDs;
- missing or inactive IDs;
- category or family mismatch;
- unknown item keys;
- malformed URLs;
- empty categories/lists;
- simultaneous `scenarios` and legacy `question_ids` forms.

The manifest stores the resolved ordered list, derived category/family counts, and `scenarios_sha256`. All arms receive the same `(question_id, sample_index)` matrix. Arm-local scenario overrides are not supported.

Legacy immutable configs may still use:

```yaml
selection:
  question_ids:
    - "<question_id>"
```

## Samples, retries, and timeout

```yaml
generation:
  samples_per_task: 5
  retry:
    max_attempts: 1
    retry_only: none
  timeout_seconds: 1800
```

The default experiment uses five independent samples per task. Timeout is read only from the frozen experiment config. Retry changes alter the execution contract and possible call count; inspect the prepared manifest.

## Credentials

Never put credential values in `config.yaml`.

The harness rejects non-empty inline fields such as:

- `api_key`;
- `access_token`;
- `password`;
- `client_secret`;
- `private_key`.

### OAuth providers

Configure OAuth in the source Hermes home, normally `~/.hermes`:

```bash
hermes auth add openai-codex
```

Generated arm homes receive an ignored runtime symlink to the source `auth.json`.

### API-key providers

List only environment-variable names:

```yaml
arms:
  moa:
    credential_env:
      - OPENROUTER_API_KEY
```

Provide the value through the process environment:

```bash
export OPENROUTER_API_KEY='your-key-here'
```

Values may also be resolved from the source Hermes `.env` or `/etc/environment`. A project-local `.env` is ignored by Git but is not loaded automatically; source it into the shell first:

```bash
set -a
. ./.env
set +a
```

For each arm, `prepare` writes only allowlisted values to an isolated `runs/<run>/homes/<arm>/.env` with mode `0600`. Child environments first have inherited key/token/secret/password variables removed, then the arm-specific Hermes home loads its allowlist. A missing allowlisted variable fails during `prepare`.

## Hermes version compatibility

The public config selects the verified reference profile:

```yaml
compatibility:
  hermes:
    profile: 0.19.1
```

The profile is code-owned. Changing the YAML string cannot declare another Hermes schema verified.

### Exact version

For Hermes `0.19.1`, `prepare` runs strict profile-specific checks:

- treatment-critical types and keys;
- generated configuration loading;
- effective provider, model, reasoning, and MoA values;
- native `config check`;
- offline `prompt-size --json`.

A failed strict probe remains a hard error. It means the nominally supported Hermes did not apply the frozen treatment as expected.

### Different version

A version mismatch is **warning-only**. `prepare` records:

```json
{
  "status": "unverified-version",
  "warning_codes": ["HERMES_VERSION_MISMATCH"]
}
```

It prints the same warning to stderr and skips profile-specific probes, because applying a `0.19.1` probe contract to an unknown schema would produce misleading evidence. `run` is allowed to make model calls with the selected binary. The actual Hermes invocation may still fail if that release cannot load or execute the arm configuration.

Scoring preserves the warning. A complete result uses `VALID_WITH_HERMES_WARNING`, not plain `VALID`.

Missing or non-executable binaries, malformed harness configuration, inline credentials, unavailable credentials, and execution failures remain hard errors.

### Executable selection

The same resolved binary is used for `--version`, offline probes, and every model invocation. Selection precedence is:

1. `--hermes-executable /absolute/path/to/hermes`;
2. `HERMES_EXECUTABLE`;
3. `hermes` on `PATH`.

An invalid explicit path is a hard error and never falls back to another installation.

### Project-local runtime

Install the verified public Hermes commit into an ignored, isolated venv:

```bash
./scripts/install-hermes-runtime.sh
HERMES="$PWD/.hermes-runtime/hermes-agent/.venv/bin/hermes"
```

The script pins full commit `dac4bbea09a342879d9769d6a5357b12b84b936c`, verifies Hermes `0.19.1`, and does not create or replace `~/.local/bin/hermes`. Override its destination only when needed:

```bash
HERMES_RUNTIME_DIR=/path/to/runtime ./scripts/install-hermes-runtime.sh
```

Provider credentials remain in the source Hermes home; runtime installation and credential setup are deliberately separate.

### Evidence and future profiles

Hermes `0.19.1`'s native `config check` is not sufficient by itself: unknown fields or invalid treatment types may otherwise be ignored. The manifest therefore stores executable/version, selected profile, per-arm effective settings when verified, config-check result, prompt-size digest, tool schema count, warning codes, and warnings.

A new verified profile still requires a code change, schema/adapter review, and tests. The harness never auto-migrates frozen configs. Use the current [Hermes configuration reference](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/) during that review.
