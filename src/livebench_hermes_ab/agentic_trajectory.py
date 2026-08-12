from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class TrajectoryStatus(StrEnum):
    SUBMITTED = "submitted"
    LIMITS_EXCEEDED = "limits_exceeded"
    COMMAND_TIMEOUT = "command_timeout"
    WALL_CLOCK_TIMEOUT = "wall_clock_timeout"
    INVALID_ACTION = "invalid_action"
    COMMAND_FAILED = "command_failed"
    MISSING_SUBMISSION = "missing_submission"


@dataclass(frozen=True)
class TrajectoryLimits:
    max_turns: int
    wall_clock_seconds: int
    command_timeout_seconds: int

    def __post_init__(self) -> None:
        if min(self.max_turns, self.wall_clock_seconds, self.command_timeout_seconds) < 1:
            raise ValueError("trajectory limits must be positive")


@dataclass(frozen=True)
class AgentAction:
    argv: tuple[str, ...] = ()
    cwd: Path = Path(".")
    submission: bool = False

    @classmethod
    def submit(cls) -> AgentAction:
        return cls(submission=True)


@dataclass(frozen=True)
class TrajectoryResult:
    status: TrajectoryStatus
    turns: int
    elapsed_seconds: float
    raw_trajectory_sha256: str
    bound_trajectory_sha256: str


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _resolve_cwd(workspace: Path, relative: Path) -> Path | None:
    if relative.is_absolute():
        return None
    root = workspace.resolve()
    resolved = (root / relative).resolve()
    return resolved if resolved == root or root in resolved.parents else None


def _run_action(action: AgentAction, workspace: Path, timeout: float) -> dict[str, object]:
    cwd = _resolve_cwd(workspace, action.cwd)
    if cwd is None or not action.argv:
        return {"kind": "invalid_action"}
    try:
        completed = subprocess.run(
            action.argv,
            cwd=cwd,
            env={"HOME": str(workspace), "PATH": os.environ.get("PATH", "")},
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "kind": "command_timeout",
            "stdout": (error.stdout or b"").decode(errors="replace"),
            "stderr": (error.stderr or b"").decode(errors="replace"),
        }
    return {
        "kind": "command",
        "argv": list(action.argv),
        "cwd": str(action.cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode(errors="replace"),
        "stderr": completed.stderr.decode(errors="replace"),
    }


def _publish_trajectory(
    records: list[dict[str, object]],
    status: TrajectoryStatus,
    started: float,
    private_root: Path,
    public_path: Path,
    context_digest: str | None,
) -> TrajectoryResult:
    elapsed = time.monotonic() - started
    raw = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    _atomic_write(private_root / "trajectory.json", raw + b"\n")
    bound = hashlib.sha256(f"{context_digest or ''}:{digest}".encode()).hexdigest()
    public = {
        "schema_version": 1,
        "status": status.value,
        "turns": len(records),
        "elapsed_seconds": elapsed,
        "raw_trajectory_sha256": digest,
        "context_digest": context_digest,
        "bound_trajectory_sha256": bound,
        "turn_digests": [
            hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
            for item in records
        ],
    }
    _atomic_write(
        public_path,
        (json.dumps(public, sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )
    return TrajectoryResult(status, len(records), elapsed, digest, bound)


def run_trajectory(
    actions: list[AgentAction],
    workspace: Path,
    private_root: Path,
    public_path: Path,
    limits: TrajectoryLimits,
    executor: Callable[[AgentAction, Path, float], dict[str, object]] = _run_action,
    context_digest: str | None = None,
) -> TrajectoryResult:
    started = time.monotonic()
    records: list[dict[str, object]] = []
    status = TrajectoryStatus.MISSING_SUBMISSION
    for action in actions:
        if len(records) >= limits.max_turns:
            status = TrajectoryStatus.LIMITS_EXCEEDED
            break
        remaining = limits.wall_clock_seconds - (time.monotonic() - started)
        if remaining <= 0:
            status = TrajectoryStatus.WALL_CLOCK_TIMEOUT
            break
        if action.submission:
            records.append({"kind": "submission"})
            status = TrajectoryStatus.SUBMITTED
            break
        record = executor(action, workspace, min(remaining, limits.command_timeout_seconds))
        records.append(record)
        kind = record["kind"]
        if kind == "invalid_action":
            status = TrajectoryStatus.INVALID_ACTION
            break
        if kind == "command_timeout":
            status = TrajectoryStatus.COMMAND_TIMEOUT
            break
        if record.get("returncode") != 0:
            status = TrajectoryStatus.COMMAND_FAILED
            break
    else:
        if len(records) >= limits.max_turns:
            status = TrajectoryStatus.LIMITS_EXCEEDED
    return _publish_trajectory(records, status, started, private_root, public_path, context_digest)
