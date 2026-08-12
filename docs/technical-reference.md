# Technical reference

The harness uses immutable domain values and explicit side-effect boundaries. `config`, `workload`, `manifest`, `trace_validation`, `resume`, `scoring`, and `report` own pure policy. `hermes`, `artifacts`, `execution`, and `scheduler` own external effects or coordination. `cli` only assembles those services.

Prepared runs and every cell journal use schema version 2. Older manifests and journals raise `UnsupportedSchemaVersion`. Cell attempts are immutable; a retry is written separately and becomes authoritative only through atomic promotion.

Each immutable attempt uses the versioned attempt-envelope schema. The envelope contains the
terminal outcome and may contain attempt-local diagnostics. In particular, a rejected MoA trace
is persisted before the isolated cell home is removed. Diagnostics are not promoted into the
authoritative cell journal and do not participate in scoring.

Execution and scoring bundles use complete generation directories with one atomic current-generation pointer. Readers never combine files from different generations. A fatal execution has no execution pointer. Scoring reads frozen terminal evidence, computes the common valid pair cohort across all arms, calculates one `ScoringResult`, and projects both JSON and Markdown from it. It does not invoke Hermes or mutate cell journals.

The scheduler admits bounded work on completion, stops admission after a harness error, cancels work that has not started, drains active futures, persists drained terminal results, and chooses simultaneous fatal errors by the lowest frozen submission index. Balanced mode groups one or more complete arm waves into each worker batch, starts every cell in the batch through a common barrier, and joins the full batch before admitting another. Its worker count must be divisible by the arm count.
