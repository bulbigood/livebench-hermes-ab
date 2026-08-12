from __future__ import annotations

import json
import sys
from pathlib import Path

from livebench_hermes_ab.agentic_trajectory import (
    AgentAction,
    TrajectoryLimits,
    TrajectoryStatus,
    run_trajectory,
)


def test_runner_submits_with_bounded_digest_only_public_journal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    private = tmp_path / ".private"
    public = tmp_path / "trajectory.json"
    actions = [
        AgentAction((sys.executable, "-c", "print('secret output')")),
        AgentAction.submit(),
    ]
    result = run_trajectory(actions, workspace, private, public, TrajectoryLimits(3, 5, 2))
    assert result.status is TrajectoryStatus.SUBMITTED
    assert result.turns == 2
    value = json.loads(public.read_text())
    assert value["status"] == "submitted"
    assert value["turns"] == 2
    assert "secret output" not in public.read_text()
    assert len(value["raw_trajectory_sha256"]) == 64
    assert (private / "trajectory.json").is_file()


def test_runner_classifies_turn_limit(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = run_trajectory(
        [AgentAction((sys.executable, "-c", "pass"))] * 2,
        workspace,
        tmp_path / ".private",
        tmp_path / "public.json",
        TrajectoryLimits(1, 5, 2),
    )
    assert result.status is TrajectoryStatus.LIMITS_EXCEEDED


def test_runner_classifies_command_timeout(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = run_trajectory(
        [AgentAction((sys.executable, "-c", "import time; time.sleep(2)"))],
        workspace,
        tmp_path / ".private",
        tmp_path / "public.json",
        TrajectoryLimits(2, 3, 1),
    )
    assert result.status is TrajectoryStatus.COMMAND_TIMEOUT


def test_runner_rejects_absolute_cwd_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = run_trajectory(
        [AgentAction((sys.executable, "-c", "pass"), cwd=Path("/tmp"))],
        workspace,
        tmp_path / ".private",
        tmp_path / "public.json",
        TrajectoryLimits(2, 3, 1),
    )
    assert result.status is TrajectoryStatus.INVALID_ACTION
