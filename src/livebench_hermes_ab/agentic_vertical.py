from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .agentic import AgenticCohort, AgenticStatus, AgenticTask, SidecarRequest, run_sidecar
from .agentic_attempts import AgenticAttemptStore
from .agentic_sandbox import PodmanWorkspaceExecutor
from .agentic_trajectory import AgentAction, TrajectoryLimits, TrajectoryStatus, run_trajectory
from .agentic_workspace import extract_candidate_patch, filter_hidden_test_changes
from .domain import HarnessExecutionError

_REPO_PATHS = {"python": "/testbed", "java": "/home/gson", "rust": "/home/bytes"}


def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, **kwargs)


def _copy_workspace(executable: str, container: str, source: str, destination: Path) -> None:
    last_error = ""
    for attempt in range(2):
        destination.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [executable, "cp", f"{container}:{source}/.git", str(destination / ".git")],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return
        last_error = completed.stderr.strip()
        shutil.rmtree(destination, ignore_errors=True)
        if attempt == 0:
            time.sleep(0.5)
    raise HarnessExecutionError(f"container workspace copy failed: {last_error[:500]}")


def _materialize_workspace(cohort: AgenticCohort, task: AgenticTask, workspace: Path) -> None:
    container = _run(
        [cohort.runtime.executable, "create", "--network", "none", task.image, "/bin/true"],
        text=True,
    ).stdout.strip()
    try:
        _copy_workspace(cohort.runtime.executable, container, _REPO_PATHS[task.language], workspace)
    finally:
        subprocess.run(
            [cohort.runtime.executable, "rm", "-f", container],
            check=False,
            capture_output=True,
        )
    image_head = _run(["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True).stdout.strip()
    ancestor = subprocess.run(
        ["git", "-C", str(workspace), "merge-base", "--is-ancestor", task.base_sha, image_head],
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise HarnessExecutionError(
            f"pinned base is not an ancestor for {task.instance_id}: "
            f"base={task.base_sha}, image_head={image_head}"
        )
    _run(["git", "-C", str(workspace), "reset", "--hard", task.base_sha])
    _run(["git", "-C", str(workspace), "clean", "-fdx"])
    actual = _run(["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True).stdout.strip()
    if actual != task.base_sha:
        raise HarnessExecutionError(
            f"workspace normalization failed for {task.instance_id}: {actual}"
        )


def _memory_mb(value: str) -> int:
    if not value.endswith("g") or not value[:-1].isdigit():
        raise HarnessExecutionError(f"unsupported runtime memory value: {value}")
    return int(value[:-1]) * 1024


def _run_task(
    cohort: AgenticCohort,
    task: AgenticTask,
    evidence_root: Path,
    output_root: Path,
    workspace: Path,
) -> dict[str, object]:
    started = time.monotonic()
    _materialize_workspace(cohort, task, workspace)
    source = evidence_root / task.instance_id
    trajectory_private = output_root / ".private" / task.instance_id / "trajectory"
    trajectory_public = output_root / "trajectories" / f"{task.instance_id}.json"
    trajectory = run_trajectory(
        [AgentAction(("git", "status", "--short")), AgentAction.submit()],
        workspace,
        trajectory_private,
        trajectory_public,
        TrajectoryLimits(max_turns=3, wall_clock_seconds=120, command_timeout_seconds=60),
        PodmanWorkspaceExecutor(
            image=task.image,
            executable=cohort.runtime.executable,
            cpus=cohort.runtime.cpus,
            memory_mb=_memory_mb(cohort.runtime.memory),
        ),
        context_digest=hashlib.sha256(
            f"trajectory-v1:{task.instance_id}:{task.base_sha}:{task.image_digest}".encode()
        ).hexdigest(),
    )
    if trajectory.status is not TrajectoryStatus.SUBMITTED:
        raise HarnessExecutionError(
            f"synthetic trajectory failed for {task.instance_id}: {trajectory.status.value}"
        )
    _run(["git", "-C", str(workspace), "apply", str((source / "fix.patch").resolve())])
    extracted = extract_candidate_patch(workspace, task.base_sha)
    filtered = filter_hidden_test_changes(extracted.content, task.hidden_test_paths)
    private = output_root / ".private" / task.instance_id
    private.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "test.patch", private / "test.patch")
    (private / "candidate.patch").write_bytes(filtered.content)
    result = run_sidecar(cohort, SidecarRequest(1, task.instance_id, "candidate", private))
    return {
        "schema_version": 1,
        "task_id": task.instance_id,
        "attempt": 1,
        "status": result.status.value,
        "reason_code": None if result.reason_code is None else result.reason_code.value,
        "patch_sha256": filtered.sha256,
        "trajectory_sha256": trajectory.bound_trajectory_sha256,
        "image_digest": result.image_digest,
        "elapsed_seconds": time.monotonic() - started,
        "removed_hidden_paths": list(filtered.removed_paths),
        "result_sha256": hashlib.sha256(result.to_json().encode()).hexdigest(),
    }


def run_no_provider_vertical(
    cohort: AgenticCohort, evidence_root: Path, output_root: Path
) -> dict[str, object]:
    store = AgenticAttemptStore(output_root)
    results = []
    with tempfile.TemporaryDirectory(prefix="livebench-agentic-workspaces-") as temporary:
        for task in cohort.tasks:
            value = _run_task(
                cohort, task, evidence_root, output_root, Path(temporary) / task.instance_id
            )
            store.publish(value)
            results.append(value)
    complete = all(item["status"] == AgenticStatus.RESOLVED.value for item in results)
    return {
        "schema_version": 1,
        "status": "complete" if complete else "failed",
        "source_revision": cohort.source_revision,
        "attempts": results,
    }
