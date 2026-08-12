# Agentic Coding Support Assessment

Status: architecture spike; no implementation or provider-backed run has been performed.

## Scope

Add LiveBench Agentic Coding as a repository-level benchmark while preserving the existing harness guarantees:

- YAML is the experiment SSOT;
- all arms receive the same frozen instances;
- execution evidence is immutable and resumable;
- infrastructure failures are distinguished from model failures;
- scoring is independent and reproducible;
- credentials, hidden tests, and rejected diagnostics do not enter published artifacts.

Pinned evidence source: LiveBench commit `00eae856aa1c1a9e9d058a65a9a94d85884034c4`.

## Upstream contract

The pinned LiveBench implementation is based on Multi-SWE-Bench-style repository issues and Mini-SWE-Agent. It is not a text-only coding benchmark.

Per instance, the runner needs:

1. a pinned repository/base revision and problem statement;
2. a task-specific container image;
3. an interactive agent session inside `/testbed`;
4. repeated model/tool turns that inspect and modify the repository;
5. a submitted Git patch;
6. filter model changes that touch hidden-test files;
7. apply the filtered patch in a fresh grading container;
8. restore hidden-test files to the pinned base, apply the hidden test patch, and run repository-specific commands;
9. parse test transitions into a resolved/unresolved/error classification.

The pinned `livebench.yaml` policy allows up to 250 agent turns, a 5,400-second wall-clock budget, and 120 seconds for individual environment commands. Agent containers are intended to run without network access to prevent fetching the gold patch or hidden tests.

Upstream warns that storing the full set of task-specific images can require up to 150 GB.

## Current compatibility gaps

### Execution model

The current harness executes one `hermes chat --quiet` process per cell and expects one answer record. Agentic Coding requires a durable repository workspace and a multi-turn tool loop. It therefore cannot be represented honestly as another objective text scorer.

Required change: introduce an execution-adapter boundary, for example:

```text
TextCellExecutor
AgenticRepositoryExecutor
```

The scheduler may continue to schedule typed cells, but admission limits for repository cells must be separate from provider-call concurrency.

### Workload and manifest

`CellSpec` currently carries a prompt, turns, profile, and a fixed expected provider-call count. Agentic instances require frozen repository metadata, image identity, test contract, tool policy, and dynamic call accounting.

Required additions include:

- workload kind (`text` or `agentic_repository`);
- repository URL/name and pinned base SHA;
- instance/image ID and immutable image digest;
- problem statement digest;
- test-patch and evaluation-contract digests;
- allowed tools and network policy;
- step, command, and wall-clock limits;
- dynamic provider-call/token/cost observations.

The existing fixed `expected_provider_calls` invariant must become workload-kind aware. For Agentic Coding, a configured upper bound and observed count are more truthful than a fixed exact count.

### Hermes arm profiles

All current arms disable terminal, file, and code-execution tools. Agentic Coding requires a dedicated profile per arm with a bounded shell/workspace adapter. Reusing the prompt-only profiles would either fail immediately or silently measure patch prose rather than repository work.

MoA also needs a policy decision. Applying a fresh reference fan-out on every one of up to 250 turns can multiply cost dramatically and changes the nature of the agent loop. The first supported slice should therefore either:

1. support plain `base` and `gpt_medium` arms only; or
2. define and validate an explicit bounded MoA turn policy before including MoA in comparisons.

It must not inherit the existing assumption of exactly two provider calls per MoA cell.

### Container runtime

The current machine has rootless Podman at `/usr/bin/podman`, but no `docker` executable. Pinned upstream code defaults to `docker`, although its Mini-SWE-Agent environment exposes an executable setting.

Required work:

- add a container-runtime adapter/configuration;
- verify Podman compatibility instead of installing a system-wide Docker daemon;
- pin image digests, not mutable tags;
- enforce no-network agent execution;
- separate build, inference, and evaluation phases;
- bound disk use and garbage collection without deleting evidence needed by active runs.

### Scoring and evidence

Agentic scoring should use upstream resolved/unresolved semantics, with infrastructure states kept separate:

- resolved;
- valid but unresolved;
- empty patch;
- inference error;
- image/build error;
- evaluation timeout/error;
- invalid or contaminated workspace.

A valid unresolved patch is a score of zero, not an exclusion. Infrastructure failures may be excluded according to a frozen policy. Patch, trajectory, command logs, and test logs are potentially sensitive and should remain attempt-local; promoted scoring evidence should contain digests and sanitized status summaries.

### Resume and isolation

A durable attempt must identify all lifecycle stages:

```text
prepared -> image_ready -> agent_running -> patch_submitted -> evaluated -> terminal
```

A retry must start from a clean pinned repository state. Reusing a mutated workspace would contaminate paired comparisons.

## Recommended architecture

Prefer a typed subprocess sidecar around the pinned upstream data and evaluator, while keeping Hermes as the agent runtime. The sidecar should emit a versioned structured result rather than exposing the leaderboard CLI as an opaque process. This gives each attempt a strong cancellation and failure boundary without coupling the harness to Hermes or LiveBench internals. Do not use a text-only surrogate.

Suggested components:

```text
agentic_domain.py       typed repository-instance and patch evidence
agentic_config.py       runtime/image/tool/limit policy
agentic_preparation.py  freeze instance metadata and image plan
agentic_runtime.py      rootless Podman workspace lifecycle
agentic_executor.py     Hermes repository session and patch capture
agentic_evaluator.py    pinned upstream evaluation adapter
agentic_artifacts.py    immutable patch/trajectory/test evidence
```

Shared scheduler and artifact-generation code should be reused only behind explicit interfaces. Avoid adding Agentic Coding conditionals throughout the text execution path.

## Delivery estimate

The estimates below assume one experienced engineer already familiar with this harness and exclude provider wait time.

### Phase 0: compatibility spike — 2 to 4 engineering days

- obtain a small pinned public Agentic Coding fixture set;
- build or pull one task image;
- run one gold patch and one empty patch through evaluation;
- verify rootless Podman compatibility and no-network execution;
- measure image size, build time, evaluation time, and cleanup behavior.

Exit criterion: one deterministic local instance can be prepared and scored without any model call.

### Phase 1: single-arm vertical slice — 5 to 8 engineering days

- typed config/domain/manifest extensions;
- one repository execution adapter;
- one plain Hermes arm with tool access;
- patch capture and immutable attempts;
- evaluator integration;
- resume, timeout, and clean-workspace behavior;
- focused deterministic tests and one provider-backed smoke.

Exit criterion: 1 to 3 instances run end-to-end with reproducible evidence.

### Phase 2: paired multi-arm support — 4 to 7 engineering days

- identical frozen instances across arms;
- per-arm isolated images/workspaces;
- balanced admission and resource caps;
- common-valid scoring plus reliability reporting;
- paired delta/report integration;
- failure taxonomy and retry policy.

Exit criterion: a small two-arm benchmark is reproducible and directly comparable.

### Phase 3: MoA qualification — 4 to 8 engineering days

- define bounded multi-turn MoA semantics;
- dynamic provider-call and token accounting;
- trajectory validation at each turn or session boundary;
- cost and timeout guards;
- focused provider-backed comparison.

This phase may be omitted initially. Blindly applying current MoA fan-out to every agent turn is not acceptable.

### Phase 4: production hardening — 3 to 6 engineering days

- larger fixture matrix;
- disk/image cache policy;
- interruption and corruption tests;
- sanitized report export;
- operational documentation and CI-compatible dry-run fixtures.

### Total

- useful plain single-arm vertical slice: approximately 7 to 12 engineering days;
- credible two-arm benchmark: approximately 11 to 19 engineering days;
- full four-arm benchmark including qualified MoA: approximately 18 to 33 engineering days.

The largest uncertainty is container/image compatibility across repositories, followed by the semantics and cost of multi-turn MoA.

## Operational cost envelope

Exact provider cost cannot be estimated from the current text benchmark because Agentic Coding call count and context grow dynamically per trajectory. Upstream allows up to 250 model turns per instance.

Use these bounded planning matrices first:

| Stage | Instances | Samples | Arms | Agent sessions | Maximum wall-clock per session |
|---|---:|---:|---:|---:|---:|
| Infrastructure smoke | 1 | 1 | 0 | 0 | evaluator only |
| Provider smoke | 1 | 1 | 1 | 1 | 90 min |
| Vertical slice | 3 | 1 | 1 | 3 | 90 min |
| Paired pilot | 3 | 1 | 2 | 6 | 90 min |
| Four-arm pilot | 3 | 1 | 4 | 12 | 90 min |
| Small benchmark | 10 | 1 | 4 | 40 | 90 min |

Do not start with five stochastic samples. Repository-task diversity matters more initially, and a `10 x 5 x 4` matrix would create 200 long-running agent sessions.

Provider spend should be bounded in YAML by all of:

- maximum turns per instance;
- maximum input/output tokens per instance;
- maximum monetary cost per instance when provider accounting supports it;
- wall-clock timeout;
- maximum concurrently active repository sessions.

A paid smoke should not be authorized until a no-model gold/empty-patch evaluation measures image and evaluator costs.

## Infrastructure implications

- Container storage: budget up to 150 GB for the complete upstream set; a focused pilot should enforce a much smaller measured quota.
- CPU/RAM: image builds and repository test suites can dominate model latency. Measure per fixture before choosing concurrency.
- Network: image preparation may require network access; agent inference and scoring should be offline wherever upstream contracts allow.
- Security: repository tests are untrusted code. Rootless containers, resource limits, no host credential mounts, and no host network are mandatory.
- CI: a full benchmark is unsuitable for ordinary PR CI. CI should use synthetic/local fixtures; paid and large-image runs should remain operator-triggered.

## Approaches considered

### A. Native typed adapter around pinned upstream evaluator — recommended

Best fit for immutable evidence, resume, fair A/B execution, and explicit failure taxonomy. More engineering work, but the result is inspectable and maintainable.

### B. Invoke upstream `run_livebench.py` as an opaque subprocess

Faster for a one-off leaderboard run, but conflicts with the harness's YAML SSOT, per-cell journals, arm fairness, credential boundary, and deterministic resume. Suitable only for an exploratory external comparison, not integrated support.

### C. Treat a repository issue as a text prompt and score the returned patch text

Rejected. It omits repository interaction and test execution, so it is not Agentic Coding.

## Recommended sequence

1. Keep this work isolated from the published scenario replacement branch.
2. Obtain read access to the authoritative Agentic Coding records.
3. Run no-provider Phase 0 admission sequentially for the six repository slots below.
4. Qualify rootless Podman and record each image digest, incremental size, build time, and shared layers.
5. Validate gold, empty, and deliberately wrong patches for every admitted record.
6. Freeze only the records that fit the 15 GB quota and implement the plain single-arm vertical slice.
7. Add a second plain arm and paired/reliability reporting.
8. Decide separately whether MoA semantics and expense justify Phase 3.

## Recommended compact multilingual cohort

The preferred cohort under a 15 GB hard run-owned storage cap has six repository slots:

| Language | Primary repository | Backup | Reason |
|---|---|---|---|
| Python | `python-attrs/attrs` | `pallets/click` | Small pytest project with an explicit adapter and no heavy native stack |
| Python | `pallets/click` | `python-attrs/attrs` | A second lightweight codebase in the same ecosystem |
| Java | `google/gson` | `junit-team/junit5` | Focused Maven library; avoids application servers and distributed systems |
| Java | `junit-team/junit5` | `google/gson` | Mature test suite and explicit JDK-dependent adapter |
| Rust | `tokio-rs/bytes` | `sharkdp/fd` | Small crate with plain `cargo test`; shares `rust:latest` layers |
| Rust | `sharkdp/fd` | `tokio-rs/bytes` | Compact CLI crate with a simple adapter |

Exclude heavyweight candidates such as Django, scikit-learn, matplotlib, Keycloak, Dubbo, Tokio itself, Helix, Nushell, and native/GUI repositories from the first cohort.

This is a repository-slot selection, not yet a frozen scenario selection. The authoritative Agentic Coding records are gated and absent from the pinned Git checkout, so exact question IDs, PR numbers, base SHAs, test patches, and image prefixes cannot be selected without access to those records. Do not invent them from adapter names.

For each slot, select exactly one PR record using these fail-closed criteria:

1. the record belongs to the named repository and pinned release;
2. its upstream adapter resolves successfully;
3. gold patch resolves and empty/wrong patches do not;
4. the measured task image keeps retained run-owned storage at or below 11 GB and total run-owned storage at or below 15 GB;
5. build and grading complete within configured limits;
6. hidden-test changes are filtered correctly;
7. no external network is required during agent execution or grading;
8. prefer the smallest measured incremental image among valid records, not the easiest issue by score.

Admission order is Python, Rust, then Java. This materializes two lighter ecosystems first and leaves the largest expected toolchain for last. Stop before admitting the next record when projected run-owned storage exceeds 15 GB or filesystem free space would fall below 6 GB.

The host has Python 3.13 and OpenJDK/Javac 21, but no Rust toolchain. Host compilers do not determine grading compatibility because Agentic Coding runs inside task images; Rust remains viable through the shared `rust:latest` base.

## Measured Phase 0 multilingual cohort

Phase 0 reconstructed a candidate pool from the public authoritative Multi-SWE-bench origin because the corresponding LiveBench datasets return HTTP 401 and are absent from the pinned checkout. This proves local evaluator and storage feasibility; it does **not** independently prove that each record is present in the gated LiveBench release.

Source:

```text
dataset:  ByteDance-Seed/Multi-SWE-bench
revision: 56ff018c04a38e27ada1e9d0a6d5839a51f88f0d
```

The minimal selected cohort is one task per requested language:

| Language | Instance | Base SHA | Evaluator command | F2P/P2P |
|---|---|---|---|---:|
| Python | `psf__requests-1142` | `22623bd8c265b78b161542663ee980738441c307` | `pytest -rA test_requests.py` | 1/5 |
| Java | `google__gson-1093` | `0aaef0fd1bb1b9729543dc40168adfb829eb75a4` | `mvn clean test -Dmaven.test.skip=false -DfailIfNoTests=false` | 1/87 |
| Rust | `tokio-rs__bytes-732` | `291df5acc94b82a48765e67eeb1c1a2074539e68` | `cargo test` | 1/9 |

Measured rootless Podman storage:

| Admission step | Final PR image size | Incremental filesystem use | Preparation time |
|---|---:|---:|---:|
| Python prebuilt image | 2.526 GB | 2.609 GB | 31.76 s pull |
| Rust base + PR image | 1.850 GB displayed PR size | 1.907 GB | 56.74 s build |
| Java base + PR image | 0.864 GB displayed PR size | 0.900 GB | 111.02 s build |
| **Retained cohort after dangling-image cleanup** | — | **5,459,492,864 bytes (5.46 GB)** | — |

The filesystem baseline was 25,706,901,504 bytes used. After validation and cleanup it was 31,166,394,368 bytes used, with 15,102,009,344 bytes still available. The retained cohort therefore uses 36.4% of the 15 GB hard cap and leaves 9.54 GB of run-owned headroom.

No-provider targeted validation used fresh rootless containers, `--network none`, two CPUs, and a 4 GB memory limit:

| Instance | Empty/test-only | Gold | Deliberately wrong |
|---|---:|---:|---:|
| `psf__requests-1142` | unresolved (`1`) | resolved (`0`) | unresolved (`1`) |
| `google__gson-1093` | unresolved (`1`) | resolved (`0`) | unresolved (`1`) |
| `tokio-rs__bytes-732` | unresolved (`101`) | resolved (`0`) | unresolved (`101`) |

Java's complete historical suite has unrelated locale/JDK-sensitive baseline failures in this image. The declared target `JsonWriterTest` nevertheless exhibits the required empty/gold/wrong behavior, so grading must continue to use upstream F2P/P2P classification rather than whole-process exit status alone.

Hidden-test isolation is valid for the selected records:

- Python model path `requests/models.py`; hidden-test path `test_requests.py`;
- Java model path `gson/src/main/java/com/google/gson/stream/JsonWriter.java`; hidden-test path `gson/src/test/java/com/google/gson/stream/JsonWriterTest.java`;
- Rust model path `src/buf/buf_impl.rs`; hidden-test path `tests/test_buf.rs`.

The sets are disjoint. In addition, pinned upstream grading derives hidden-test paths from `test_patch`, restores those paths from the pinned base SHA, and only then applies the hidden test patch. Attempts by a model patch to modify hidden-test files are therefore overwritten before grading. Gold and hidden-test patch contents remain only in ignored local evidence.

All validation containers were created with `--rm`; final container count was zero. A dangling-image prune was executed after measurement; Podman retained build ancestry layers, and those layers are included in the measured 5.46 GB total. The three selected final images remain cached for the next evaluator step.

## Current go/no-go assessment

Go for a single-arm no-provider sidecar implementation using the measured three-task cohort. Do not run provider-backed Agentic Coding and do not claim official LiveBench cohort membership until the gated records are available and identity-matched.

The storage question is resolved: the multilingual cohort fits comfortably below 15 GB. Remaining blockers are the typed sidecar contract, exact gated-release identity confirmation, and full upstream F2P/P2P report execution—not local disk capacity.
