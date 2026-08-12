from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import yaml

from .domain import ConfigError

Mode = Literal["empty", "gold", "wrong", "candidate"]


class AgenticStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    INVALID_PATCH = "invalid_patch"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


class AgenticReasonCode(str, Enum):
    MISSING_PATCH = "MISSING_PATCH"
    PATCH_DIGEST_MISMATCH = "PATCH_DIGEST_MISMATCH"
    UNKNOWN_TASK = "UNKNOWN_TASK"
    IMAGE_DIGEST_MISMATCH = "IMAGE_DIGEST_MISMATCH"
    STORAGE_QUOTA_EXCEEDED = "STORAGE_QUOTA_EXCEEDED"
    INSUFFICIENT_FREE_SPACE = "INSUFFICIENT_FREE_SPACE"
    GRADER_TIMEOUT = "GRADER_TIMEOUT"
    CONTAINER_RUNTIME_FAILURE = "CONTAINER_RUNTIME_FAILURE"
    UNEXPECTED_TEST_RESULT = "UNEXPECTED_TEST_RESULT"


@dataclass(frozen=True, slots=True)
class StoragePolicy:
    hard_limit_bytes: int
    minimum_free_bytes: int
    measured_retained_bytes: int


@dataclass(frozen=True, slots=True)
class RuntimePolicy:
    executable: str
    network: str
    cpus: int
    memory: str
    timeout_seconds: int


@dataclass(frozen=True, slots=True)
class AgenticTask:
    instance_id: str
    language: str
    repository: str
    pr_number: int
    base_sha: str
    image: str
    image_digest: str
    fix_patch_sha256: str
    test_patch_sha256: str
    model_paths: tuple[str, ...]
    hidden_test_paths: tuple[str, ...]
    commands: Mapping[Mode, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "commands", MappingProxyType(dict(self.commands)))


@dataclass(frozen=True, slots=True)
class AgenticCohort:
    schema_version: int
    source_dataset: str
    source_revision: str
    source_relationship: str
    storage: StoragePolicy
    runtime: RuntimePolicy
    tasks: tuple[AgenticTask, ...]

    @property
    def by_id(self) -> Mapping[str, AgenticTask]:
        return MappingProxyType({task.instance_id: task for task in self.tasks})


@dataclass(frozen=True, slots=True)
class SidecarRequest:
    schema_version: int
    task_id: str
    mode: Mode
    evidence_dir: Path

    @classmethod
    def from_json(cls, value: str) -> SidecarRequest:
        try:
            raw = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ConfigError("invalid sidecar request JSON") from exc
        _keys(raw, {"schema_version", "task_id", "mode", "evidence_dir"}, "request")
        if raw["schema_version"] != 1 or raw["mode"] not in {
            "empty",
            "gold",
            "wrong",
            "candidate",
        }:
            raise ConfigError("unsupported sidecar request")
        return cls(1, str(raw["task_id"]), raw["mode"], Path(raw["evidence_dir"]))


@dataclass(frozen=True, slots=True)
class StorageSnapshot:
    run_owned_bytes: int
    available_bytes: int


@dataclass(frozen=True, slots=True)
class SidecarResult:
    schema_version: int
    task_id: str
    mode: str
    status: AgenticStatus
    reason_code: AgenticReasonCode | None
    image_digest: str | None
    patch_sha256: str | None
    elapsed_seconds: float
    exit_code: int | None
    stdout_sha256: str | None
    stderr_sha256: str | None

    def to_json(self) -> str:
        value = {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "mode": self.mode,
            "status": self.status.value,
            "reason_code": None if self.reason_code is None else self.reason_code.value,
            "image_digest": self.image_digest,
            "patch_sha256": self.patch_sha256,
            "elapsed_seconds": self.elapsed_seconds,
            "exit_code": self.exit_code,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
        }
        return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def _keys(value: object, expected: set[str], context: str) -> None:
    if not isinstance(value, dict):
        raise ConfigError(f"{context} must be a mapping")
    missing, unknown = expected - set(value), set(value) - expected
    if missing:
        raise ConfigError(f"{context} missing required keys: {sorted(missing)}")
    if unknown:
        raise ConfigError(f"{context} unsupported keys: {sorted(unknown)}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def load_agentic_cohort(path: Path) -> AgenticCohort:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot load agentic cohort: {path}") from exc
    _keys(raw, {"schema_version", "source", "storage", "runtime", "tasks"}, "cohort")
    if raw["schema_version"] != 1:
        raise ConfigError("agentic cohort schema version 1 is required")
    source, storage, runtime = raw["source"], raw["storage"], raw["runtime"]
    _keys(source, {"dataset", "revision", "relationship"}, "source")
    _keys(storage, {"hard_limit_bytes", "minimum_free_bytes", "measured_retained_bytes"}, "storage")
    _keys(runtime, {"executable", "network", "cpus", "memory", "timeout_seconds"}, "runtime")
    task_keys = {
        "instance_id",
        "language",
        "repository",
        "pr_number",
        "base_sha",
        "image",
        "image_digest",
        "fix_patch_sha256",
        "test_patch_sha256",
        "model_paths",
        "hidden_test_paths",
        "commands",
    }
    tasks = []
    for index, task in enumerate(raw["tasks"]):
        _keys(task, task_keys, f"tasks[{index}]")
        _keys(
            task["commands"],
            {"empty", "gold", "wrong", "candidate"},
            f"tasks[{index}].commands",
        )
        if set(task["model_paths"]) & set(task["hidden_test_paths"]):
            raise ConfigError(f"tasks[{index}] model and hidden-test paths overlap")
        tasks.append(
            AgenticTask(
                str(task["instance_id"]),
                str(task["language"]),
                str(task["repository"]),
                int(task["pr_number"]),
                str(task["base_sha"]),
                str(task["image"]),
                str(task["image_digest"]),
                str(task["fix_patch_sha256"]),
                str(task["test_patch_sha256"]),
                tuple(map(str, task["model_paths"])),
                tuple(map(str, task["hidden_test_paths"])),
                task["commands"],
            )
        )
    if len({task.instance_id for task in tasks}) != len(tasks):
        raise ConfigError("duplicate agentic task ID")
    return AgenticCohort(
        1,
        str(source["dataset"]),
        str(source["revision"]),
        str(source["relationship"]),
        StoragePolicy(**{key: int(value) for key, value in storage.items()}),
        RuntimePolicy(
            str(runtime["executable"]),
            str(runtime["network"]),
            int(runtime["cpus"]),
            str(runtime["memory"]),
            int(runtime["timeout_seconds"]),
        ),
        tuple(tasks),
    )


class PodmanBackend:
    def __init__(
        self,
        run: Callable[..., object] = subprocess.run,
        storage_probe: Callable[[], StorageSnapshot] | None = None,
    ) -> None:
        self._run = run
        self._storage_probe = storage_probe or self._default_storage_probe

    @staticmethod
    def _default_storage_probe() -> StorageSnapshot:
        usage = shutil.disk_usage(Path.home())
        completed = subprocess.run(
            ["podman", "system", "df", "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        raw = json.loads(completed.stdout)
        images = next((item for item in raw if item.get("Type") == "Images"), {})
        return StorageSnapshot(int(images.get("RawSize", 0)), usage.free)

    def preflight(
        self, policy: StoragePolicy, snapshot: StorageSnapshot | None = None
    ) -> SidecarResult:
        current = snapshot or self._storage_probe()
        if current.run_owned_bytes > policy.hard_limit_bytes:
            return _result(
                "",
                "preflight",
                AgenticStatus.INFRASTRUCTURE_FAILURE,
                AgenticReasonCode.STORAGE_QUOTA_EXCEEDED,
            )
        if current.available_bytes < policy.minimum_free_bytes:
            return _result(
                "",
                "preflight",
                AgenticStatus.INFRASTRUCTURE_FAILURE,
                AgenticReasonCode.INSUFFICIENT_FREE_SPACE,
            )
        return _result("", "preflight", AgenticStatus.RESOLVED)

    def inspect_digest(self, executable: str, image: str) -> str:
        completed = self._run(
            [executable, "image", "inspect", "--format", "{{.Digest}}", image],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return completed.stdout.strip() if completed.returncode == 0 else ""

    def grade(self, cohort: AgenticCohort, task: AgenticTask, request: SidecarRequest) -> object:
        command = [
            cohort.runtime.executable,
            "run",
            "--rm",
            "--network",
            cohort.runtime.network,
            "--cpus",
            str(cohort.runtime.cpus),
            "--memory",
            cohort.runtime.memory,
        ]
        command += ["-v", f"{request.evidence_dir.resolve()}:/evidence:ro,Z"]
        command += [task.image, "/bin/bash", "-c", task.commands[request.mode]]
        return self._run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=cohort.runtime.timeout_seconds,
            env={**os.environ, "LIVEBENCH_AGENTIC_MODE": request.mode},
        )


def _result(
    task_id: str,
    mode: str,
    status: AgenticStatus,
    reason: AgenticReasonCode | None = None,
    *,
    image_digest: str | None = None,
    patch_sha256: str | None = None,
    elapsed: float = 0.0,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
) -> SidecarResult:
    return SidecarResult(
        1,
        task_id,
        mode,
        status,
        reason,
        image_digest,
        patch_sha256,
        elapsed,
        exit_code,
        None if stdout is None else _text_digest(stdout),
        None if stderr is None else _text_digest(stderr),
    )


def _validate_evidence(
    task: AgenticTask, request: SidecarRequest
) -> tuple[str | None, SidecarResult | None]:
    required = [request.evidence_dir / "test.patch"]
    if request.mode == "gold":
        required.append(request.evidence_dir / "fix.patch")
    if request.mode == "candidate":
        required.append(request.evidence_dir / "candidate.patch")
    if any(not path.is_file() for path in required):
        return None, _result(
            request.task_id,
            request.mode,
            AgenticStatus.INVALID_PATCH,
            AgenticReasonCode.MISSING_PATCH,
        )
    expected = {"test.patch": task.test_patch_sha256, "fix.patch": task.fix_patch_sha256}
    if any(path.name in expected and _sha256(path) != expected[path.name] for path in required):
        return None, _result(
            request.task_id,
            request.mode,
            AgenticStatus.INVALID_PATCH,
            AgenticReasonCode.PATCH_DIGEST_MISMATCH,
        )
    patch_name = {
        "gold": "fix.patch",
        "candidate": "candidate.patch",
        "empty": "test.patch",
        "wrong": "test.patch",
    }[request.mode]
    return _sha256(request.evidence_dir / patch_name), None


def _classify_completed(
    task: AgenticTask, request: SidecarRequest, completed: object, elapsed: float, patch_digest: str
) -> SidecarResult:
    passed = completed.returncode == 0
    status = AgenticStatus.RESOLVED if passed else AgenticStatus.UNRESOLVED
    reason = None
    if request.mode != "candidate" and passed != (request.mode == "gold"):
        reason = AgenticReasonCode.UNEXPECTED_TEST_RESULT
    return _result(
        request.task_id,
        request.mode,
        status,
        reason,
        image_digest=task.image_digest,
        patch_sha256=patch_digest,
        elapsed=elapsed,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_sidecar(
    cohort: AgenticCohort, request: SidecarRequest, backend: PodmanBackend | None = None
) -> SidecarResult:
    backend = backend or PodmanBackend()
    task = cohort.by_id.get(request.task_id)
    if task is None:
        return _result(
            request.task_id,
            request.mode,
            AgenticStatus.INFRASTRUCTURE_FAILURE,
            AgenticReasonCode.UNKNOWN_TASK,
        )
    preflight = backend.preflight(cohort.storage)
    if preflight.status is not AgenticStatus.RESOLVED:
        return _result(request.task_id, request.mode, preflight.status, preflight.reason_code)
    patch_digest, invalid = _validate_evidence(task, request)
    if invalid is not None:
        return invalid
    assert patch_digest is not None
    try:
        image_digest = backend.inspect_digest(cohort.runtime.executable, task.image)
        if image_digest != task.image_digest:
            return _result(
                request.task_id,
                request.mode,
                AgenticStatus.INFRASTRUCTURE_FAILURE,
                AgenticReasonCode.IMAGE_DIGEST_MISMATCH,
                image_digest=image_digest,
            )
        started = time.monotonic()
        completed = backend.grade(cohort, task, request)
        elapsed = time.monotonic() - started
    except subprocess.TimeoutExpired:
        return _result(
            request.task_id,
            request.mode,
            AgenticStatus.TIMEOUT,
            AgenticReasonCode.GRADER_TIMEOUT,
            image_digest=task.image_digest,
            patch_sha256=patch_digest,
        )
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return _result(
            request.task_id,
            request.mode,
            AgenticStatus.INFRASTRUCTURE_FAILURE,
            AgenticReasonCode.CONTAINER_RUNTIME_FAILURE,
            image_digest=task.image_digest,
            patch_sha256=patch_digest,
        )
    return _classify_completed(task, request, completed, elapsed, patch_digest)
