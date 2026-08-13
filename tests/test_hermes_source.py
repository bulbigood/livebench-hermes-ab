import subprocess
from pathlib import Path

import pytest

from livebench_hermes_ab.config import HermesSourceConfig
from livebench_hermes_ab.domain import HarnessExecutionError
from livebench_hermes_ab.hermes import resolve_hermes_command, verify_hermes_source


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_directory_mode_resolves_repo_launcher(tmp_path: Path) -> None:
    launcher = tmp_path / "hermes"
    launcher.write_text("#!/bin/sh\n")
    launcher.chmod(0o755)
    source = HermesSourceConfig(mode="directory", directory=str(tmp_path))
    assert resolve_hermes_command(source, tmp_path) == (str(launcher),)


def test_directory_mode_fails_closed_without_launcher(tmp_path: Path) -> None:
    source = HermesSourceConfig(mode="directory", directory=str(tmp_path))
    with pytest.raises(HarnessExecutionError, match="Hermes executable not found"):
        resolve_hermes_command(source, tmp_path)


def test_directory_checkout_uses_its_own_uv_project(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0.1.0'\n")
    (tmp_path / "uv.lock").write_text("version = 1\n")
    monkeypatch.setattr("livebench_hermes_ab.hermes.shutil.which", lambda name: "/bin/uv")
    source = HermesSourceConfig(mode="directory", directory=str(tmp_path))

    assert resolve_hermes_command(source, tmp_path) == (
        "/bin/uv",
        "run",
        "--project",
        str(tmp_path),
        "--locked",
        "hermes",
    )


def test_git_mode_verifies_repository_and_exact_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "fake@example.test")
    _git(repo, "config", "user.name", "Fake")
    (repo / "hermes").write_text("#!/bin/sh\n")
    (repo / "hermes").chmod(0o755)
    _git(repo, "add", "hermes")
    _git(repo, "commit", "-qm", "fixture")
    commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "remote", "add", "origin", str(repo))
    source = HermesSourceConfig(mode="git", repository=str(repo), commit=commit)

    assert verify_hermes_source(source, repo) == commit

    wrong = HermesSourceConfig(mode="git", repository=str(repo), commit="0" * 40)
    with pytest.raises(HarnessExecutionError, match="commit mismatch"):
        verify_hermes_source(wrong, repo)