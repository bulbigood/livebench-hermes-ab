from __future__ import annotations

import subprocess
from pathlib import Path

from livebench_hermes_ab.agentic_sandbox import PodmanWorkspaceExecutor
from livebench_hermes_ab.agentic_trajectory import AgentAction


def test_podman_executor_has_closed_sandbox_contract(tmp_path: Path, monkeypatch) -> None:
    seen = []

    def fake_run(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, b"ok", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = PodmanWorkspaceExecutor("task-image")(
        AgentAction(("git", "status", "--short")), tmp_path, 12
    )
    command = seen[0][0]
    assert result["returncode"] == 0
    assert command[:2] == ["podman", "run"]
    assert "--rm" in command
    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert "no-new-privileges" in command
    assert command[command.index("--cap-drop") + 1] == "all"
    mounts = [command[index + 1] for index, item in enumerate(command) if item == "-v"]
    assert mounts == [f"{tmp_path.resolve()}:/workspace:rw"]
    assert not any("evidence" in item for item in command)
