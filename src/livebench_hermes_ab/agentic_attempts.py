from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .domain import PersistenceError

_ALLOWED = {
    "schema_version",
    "task_id",
    "attempt",
    "status",
    "reason_code",
    "patch_sha256",
    "trajectory_sha256",
    "image_digest",
    "elapsed_seconds",
    "removed_hidden_paths",
    "result_sha256",
}
_REQUIRED = {
    "schema_version",
    "task_id",
    "attempt",
    "status",
    "patch_sha256",
    "trajectory_sha256",
    "image_digest",
    "elapsed_seconds",
}


class AgenticAttemptStore:
    def __init__(self, root: Path):
        self.root = root

    def publish(self, value: dict[str, object]) -> Path:
        unknown = set(value) - _ALLOWED
        missing = _REQUIRED - set(value)
        if unknown or missing:
            raise PersistenceError(
                f"invalid agentic attempt fields: unknown={sorted(unknown)}, missing={sorted(missing)}"
            )
        task = str(value["task_id"]).replace("/", "_")
        attempt = value["attempt"]
        if not isinstance(attempt, int) or attempt < 1:
            raise PersistenceError("attempt number must be positive")
        path = self.root / "agentic-attempts" / f"{task}-attempt-{attempt}.json"
        if path.exists():
            raise PersistenceError(f"attempt artifact already exists: {path.name}")
        content = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if path.exists():
                raise PersistenceError(f"attempt artifact already exists: {path.name}")
            os.link(temporary, path)
            directory = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except FileExistsError as exc:
            raise PersistenceError(f"attempt artifact already exists: {path.name}") from exc
        finally:
            Path(temporary).unlink(missing_ok=True)
        return path
