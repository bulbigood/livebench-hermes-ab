from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from livebench_hermes_ab.agentic_attempts import AgenticAttemptStore
from livebench_hermes_ab.agentic_workspace import (
    PatchExtractionError,
    extract_candidate_patch,
    filter_hidden_test_changes,
)
from livebench_hermes_ab.domain import PersistenceError


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def test_extracts_patch_from_isolated_git_workspace(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "src.py").write_text("old\n")
    _git(tmp_path, "add", "src.py")
    _git(tmp_path, "commit", "-qm", "base")
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (tmp_path / "src.py").write_text("new\n")

    patch = extract_candidate_patch(tmp_path, base)
    assert b"diff --git a/src.py b/src.py" in patch.content
    assert patch.paths == ("src.py",)
    assert len(patch.sha256) == 64


def test_empty_workspace_patch_fails_closed(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "src.py").write_text("same\n")
    _git(tmp_path, "add", "src.py")
    _git(tmp_path, "commit", "-qm", "base")
    with pytest.raises(PatchExtractionError, match="empty"):
        extract_candidate_patch(tmp_path, "HEAD")


def test_hidden_test_sections_are_removed_without_touching_model_changes() -> None:
    raw = b"""diff --git a/src.py b/src.py
index 1111111..2222222 100644
--- a/src.py
+++ b/src.py
@@ -1 +1 @@
-old
+new
diff --git a/tests/test_hidden.py b/tests/test_hidden.py
index 3333333..4444444 100644
--- a/tests/test_hidden.py
+++ b/tests/test_hidden.py
@@ -1 +1 @@
-fail
+pass
"""
    filtered = filter_hidden_test_changes(raw, ("tests/test_hidden.py",))
    assert filtered.removed_paths == ("tests/test_hidden.py",)
    assert filtered.paths == ("src.py",)
    assert b"tests/test_hidden.py" not in filtered.content
    assert b"src.py" in filtered.content


def test_patch_containing_only_hidden_tests_becomes_invalid() -> None:
    raw = b"""diff --git a/tests/test_hidden.py b/tests/test_hidden.py
--- a/tests/test_hidden.py
+++ b/tests/test_hidden.py
@@ -1 +1 @@
-fail
+pass
"""
    with pytest.raises(PatchExtractionError, match="only hidden-test"):
        filter_hidden_test_changes(raw, ("tests/test_hidden.py",))


def test_attempt_store_is_exclusive_atomic_and_sanitized(tmp_path: Path) -> None:
    store = AgenticAttemptStore(tmp_path)
    value = {
        "schema_version": 1,
        "task_id": "task",
        "attempt": 1,
        "status": "resolved",
        "patch_sha256": "a" * 64,
        "trajectory_sha256": "b" * 64,
        "image_digest": "sha256:" + "c" * 64,
        "elapsed_seconds": 1.2,
    }
    path = store.publish(value)
    loaded = json.loads(path.read_text())
    assert loaded == value
    assert "patch" not in loaded
    with pytest.raises(PersistenceError, match="already exists"):
        store.publish(value)
