# Agentic Coding sidecar schema v1

The Agentic Coding backend is a separate subprocess boundary. It does not reuse prompt-cell outcomes.

## Frozen cohort

`config/agentic-coding-phase0.yaml` pins:

- source dataset and revision;
- task, repository, PR, and base SHA;
- image reference and digest;
- fix/test patch digests, never patch contents;
- model and hidden-test paths;
- fixed evaluator commands;
- runtime limits and storage gates.

Unknown or missing keys fail closed. Model and hidden-test paths must be disjoint.

The current source relationship is `public_authoritative_origin_livebench_membership_unconfirmed`. The records come from the pinned public Multi-SWE-bench origin; official gated LiveBench membership must be identity-matched before a report claims official LiveBench coverage.

## Request

```json
{
  "schema_version": 1,
  "task_id": "psf__requests-1142",
  "mode": "gold",
  "evidence_dir": "/absolute/private/evidence/path"
}
```

`mode` is one of `empty`, `gold`, `wrong`, or `candidate`. Commands cannot be supplied by the request. The sidecar executes only commands frozen in the cohort. Candidate mode requires a filtered `candidate.patch`; pinned hidden test evidence remains private.

## Bounded trajectory boundary

The provider-neutral trajectory runner accepts structured argv actions rather than shell strings. The Podman executor mounts only the isolated repository workspace, disables networking, uses a read-only root filesystem, drops all capabilities, enables `no-new-privileges`, and applies CPU, memory, PID, per-command, turn, and wall-clock limits. Raw command output is stored only under the private run directory. Public trajectory evidence contains status, timing, per-turn digests, a raw-trajectory digest, and a task/base/image-bound trajectory digest.

The current no-provider vertical uses a fake model adapter that emits strict JSON actions, receives real sandbox observations, and submits after two turns. An explicitly test-only deterministic patch applicator th...[truncated]

## Result

```json
{
  "schema_version": 1,
  "task_id": "psf__requests-1142",
  "mode": "gold",
  "status": "resolved",
  "reason_code": null,
  "image_digest": "sha256:...",
  "patch_sha256": "...",
  "elapsed_seconds": 0.5,
  "exit_code": 0,
  "stdout_sha256": "...",
  "stderr_sha256": "..."
}
```

Statuses:

- `resolved`
- `unresolved`
- `invalid_patch`
- `timeout`
- `infrastructure_failure`

Reason codes:

- `MISSING_PATCH`
- `PATCH_DIGEST_MISMATCH`
- `UNKNOWN_TASK`
- `IMAGE_DIGEST_MISMATCH`
- `STORAGE_QUOTA_EXCEEDED`
- `INSUFFICIENT_FREE_SPACE`
- `GRADER_TIMEOUT`
- `CONTAINER_RUNTIME_FAILURE`
- `UNEXPECTED_TEST_RESULT`

Output contains digests rather than raw test logs or patch contents.

## Phase 0 invocation

```bash
livebench-agentic-sidecar \
  --cohort config/agentic-coding-phase0.yaml \
  phase0 \
  --evidence-root /private/evidence/root \
  --output /private/run/result.json
```

Phase 0 executes all tasks sequentially in `empty`, `gold`, and `wrong` modes. It succeeds only when gold resolves and both controls remain unresolved. Grading uses fresh rootless containers, no network, fixed CPU/memory limits, and `--rm` cleanup.
