from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from livebench_hermes_ab.agentic import (
    AgenticReasonCode,
    AgenticStatus,
    PodmanBackend,
    SidecarRequest,
    StorageSnapshot,
    load_agentic_cohort,
    run_sidecar,
)
from livebench_hermes_ab.agentic_cli import _atomic_write
from livebench_hermes_ab.domain import ConfigError

COHORT = Path("config/agentic-coding-phase0.yaml")


def test_frozen_cohort_is_strict_and_multilingual() -> None:
    cohort = load_agentic_cohort(COHORT)
    assert cohort.schema_version == 1
    assert cohort.source_revision == "56ff018c04a38e27ada1e9d0a6d5839a51f88f0d"
    assert [task.language for task in cohort.tasks] == ["python", "java", "rust"]
    assert [task.instance_id for task in cohort.tasks] == [
        "psf__requests-1142",
        "google__gson-1093",
        "tokio-rs__bytes-732",
    ]
    assert cohort.storage.hard_limit_bytes == 15_000_000_000
    assert all(task.image_digest.startswith("sha256:") for task in cohort.tasks)


def test_cohort_rejects_unknown_keys(tmp_path: Path) -> None:
    value = COHORT.read_text() + "\nlegacy: true\n"
    path = tmp_path / "bad.yaml"
    path.write_text(value)
    with pytest.raises(ConfigError, match="unsupported keys"):
        load_agentic_cohort(path)


def test_request_round_trip_and_hidden_paths_are_not_model_paths(tmp_path: Path) -> None:
    request = SidecarRequest.from_json(
        json.dumps(
            {
                "schema_version": 1,
                "task_id": "psf__requests-1142",
                "mode": "gold",
                "evidence_dir": str(tmp_path),
            }
        )
    )
    assert request.mode == "gold"
    assert request.task_id == "psf__requests-1142"
    candidate = SidecarRequest.from_json(
        json.dumps(
            {
                "schema_version": 1,
                "task_id": "psf__requests-1142",
                "mode": "candidate",
                "evidence_dir": str(tmp_path),
            }
        )
    )
    assert candidate.mode == "candidate"
    task = load_agentic_cohort(COHORT).by_id[request.task_id]
    assert set(task.model_paths).isdisjoint(task.hidden_test_paths)


def test_quota_preflight_fails_closed() -> None:
    cohort = load_agentic_cohort(COHORT)
    backend = PodmanBackend(run=lambda *args, **kwargs: None)
    result = backend.preflight(
        cohort.storage,
        StorageSnapshot(run_owned_bytes=15_000_000_001, available_bytes=20_000_000_000),
    )
    assert result.status is AgenticStatus.INFRASTRUCTURE_FAILURE
    assert result.reason_code is AgenticReasonCode.STORAGE_QUOTA_EXCEEDED


def test_sidecar_classifies_resolved_unresolved_and_invalid_patch(tmp_path: Path) -> None:
    cohort = load_agentic_cohort(COHORT)
    task = cohort.by_id["psf__requests-1142"]
    (tmp_path / "fix.patch").write_text("fix")
    (tmp_path / "test.patch").write_text("test")
    task = replace(
        task,
        fix_patch_sha256=hashlib.sha256(b"fix").hexdigest(),
        test_patch_sha256=hashlib.sha256(b"test").hexdigest(),
    )
    cohort = replace(cohort, tasks=(task,))
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        mode = kwargs["env"]["LIVEBENCH_AGENTIC_MODE"]
        code = {"gold": 0, "empty": 1, "wrong": 1}[mode]
        return SimpleNamespace(returncode=code, stdout="tests", stderr="")

    backend = PodmanBackend(run=fake_run, storage_probe=lambda: StorageSnapshot(1, 20_000_000_000))
    backend.inspect_digest = lambda executable, image: task.image_digest  # type: ignore[method-assign]
    for mode, expected in (
        ("gold", AgenticStatus.RESOLVED),
        ("empty", AgenticStatus.UNRESOLVED),
        ("wrong", AgenticStatus.UNRESOLVED),
    ):
        result = run_sidecar(
            cohort,
            SidecarRequest(1, task.instance_id, mode, tmp_path),
            backend,
        )
        assert result.status is expected
        assert result.image_digest == task.image_digest
        assert result.patch_sha256 is not None

    (tmp_path / "fix.patch").unlink()
    result = run_sidecar(
        cohort,
        SidecarRequest(1, task.instance_id, "gold", tmp_path),
        backend,
    )
    assert result.status is AgenticStatus.INVALID_PATCH
    assert result.reason_code is AgenticReasonCode.MISSING_PATCH
    assert len(calls) == 3


def test_atomic_output_replaces_complete_file(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.write_text("stale")
    _atomic_write(target, '{"status":"complete"}\n')
    assert target.read_text() == '{"status":"complete"}\n'
    assert list(tmp_path.iterdir()) == [target]


def test_sidecar_rejects_unknown_task(tmp_path: Path) -> None:
    cohort = load_agentic_cohort(COHORT)
    result = run_sidecar(
        cohort,
        SidecarRequest(1, "unknown", "empty", tmp_path),
        PodmanBackend(run=lambda *args, **kwargs: None),
    )
    assert result.status is AgenticStatus.INFRASTRUCTURE_FAILURE
    assert result.reason_code is AgenticReasonCode.UNKNOWN_TASK
