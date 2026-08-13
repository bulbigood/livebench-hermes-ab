# Configuration

`config.yaml` has one strict schema. Required top-level sections are `experiment`, `selection`, `generation`, `execution`, `compatibility`, `arms`, and `scoring`; unknown or missing keys fail closed.

Arm mapping order is declaration order and becomes the mandatory manifest `arm_order`. The default order is `base`, `gpt_medium`, `moa_minimax`, `moa_mimo`. `execution.mode` is either `streaming` or `balanced_waves`. Retry behavior is represented once by `generation.retry.max_attempts` and `retryable_codes`. The scoring contract must name `livebench-objective-ground-truth` with schema version 2.

The scoring contract also accepts optional statistical precision settings:

```yaml
scoring:
  implementation: livebench-objective-ground-truth
  schema_version: 2
  confidence_level: 0.95
  target_margin_of_error: 0.05
```

Their defaults are 95% confidence and ±0.05 score units. They are frozen in
`config.snapshot.yaml`; rescoring therefore does not depend on the caller's current config.

Samples, scheduling mode, and worker count have one source of truth:
`generation.samples_per_task`, `execution.mode`, and `execution.workers` in the YAML
configuration. `prepare` freezes that configuration without CLI field overrides.

`balanced_waves` requires an explicit worker count divisible by the number of arms.
Each worker batch contains only complete arm waves and starts through a common barrier.
For four arms, valid values are 4, 8, 12, and so on. A value such as 7 is rejected
before provider calls can be scheduled.

Plain and MoA arms use their Hermes configuration directly. Credentials are named only in
`credential_env`; secret values must never be placed in experiment YAML.

`prepare` resolves each allowlisted name in this order:

1. the environment inherited by the harness process;
2. the dotenv file passed with `prepare --credentials-file PATH`;
3. when that option is omitted, `$HERMES_HOME/.env` (or `~/.hermes/.env`).

Only allowlisted names are copied to the isolated arm homes, with mode `0600`. The source path
and secret values are not written to `config.snapshot.yaml` or `manifest.json`. This contract is
portable across Linux and macOS: shell startup files, `/etc/environment`, systemd units, and
launchd plists are intentionally not auto-discovered or interpreted. Arrange for the launching
process to inherit the variables, or point `--credentials-file` at a dotenv file managed by the
operator's secret tooling.

Legacy flat generation retries, alternate scheduling booleans, two-arm configuration, and missing scoring contracts are unsupported.

The Markdown report is intentionally compact: distribution tables show `n`, mean, median, and
p95, with absolute arm values separated from paired deltas. Every report starts with the resolved
Hermes source and embeds the complete frozen configuration in a collapsed `<details>` block. A
Git source is rendered as repository plus exact commit; legacy release-only evidence explicitly
states when no source commit was recorded. Detailed sample variance, standard deviation, standard
error, confidence intervals, pooled within-task variance, and all percentiles remain available in
`summary.json`. The Markdown sampling section retains the recommended `samples_per_task`; with
fewer than five repeated samples per task it warns that the pilot is too small for a stable
estimate. Recommendations use observed pooled within-task variance and the configured confidence
and margin. Zero or unavailable pilot variance uses a conservative variance bound for scores in
`[0,1]`. The estimate should be recomputed after a larger wave because future variance can differ
from the pilot.
