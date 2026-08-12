# Configuration

`config.yaml` has one strict schema. Required top-level sections are `experiment`, `selection`, `generation`, `execution`, `compatibility`, `arms`, and `scoring`; unknown or missing keys fail closed.

Arm mapping order is declaration order and becomes the mandatory manifest `arm_order`. The default order is `base`, `gpt_medium`, `moa_minimax`, `moa_mimo`. `execution.mode` is either `streaming` or `balanced_waves`. Retry behavior is represented once by `generation.retry.max_attempts` and `retryable_codes`. The scoring contract must name `livebench-objective-ground-truth` with schema version 2.

Samples, scheduling mode, and worker count have one source of truth:
`generation.samples_per_task`, `execution.mode`, and `execution.workers` in the YAML
configuration. `prepare` freezes that configuration without CLI field overrides.

`balanced_waves` requires an explicit worker count divisible by the number of arms.
Each worker batch contains only complete arm waves and starts through a common barrier.
For four arms, valid values are 4, 8, 12, and so on. A value such as 7 is rejected
before provider calls can be scheduled.

Plain and MoA arms use their Hermes configuration directly. Credentials are named only in `credential_env`; secret values must remain in the environment and are never copied into artifacts.

Legacy flat generation retries, alternate scheduling booleans, two-arm configuration, and missing scoring contracts are unsupported.
