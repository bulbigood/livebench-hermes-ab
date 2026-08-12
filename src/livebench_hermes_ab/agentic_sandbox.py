from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .agentic_trajectory import AgentAction


@dataclass(frozen=True)
class PodmanWorkspaceExecutor:
    image: str
    executable: str = "podman"
    cpus: int = 2
    memory_mb: int = 4096

    def __call__(self, action: AgentAction, workspace: Path, timeout: float) -> dict[str, object]:
        if action.cwd.is_absolute() or not action.argv:
            return {"kind": "invalid_action"}
        cwd = Path("/workspace") / action.cwd
        command = [
            self.executable,
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cpus",
            str(self.cpus),
            "--memory",
            f"{self.memory_mb}m",
            "--pids-limit",
            "512",
            "--userns",
            "keep-id",
            "--security-opt",
            "no-new-privileges",
            "--cap-drop",
            "all",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=256m",
            "--tmpfs",
            "/home/agent:rw,nosuid,nodev,size=64m",
            "-e",
            "HOME=/home/agent",
            "-e",
            "PAGER=cat",
            "-v",
            f"{workspace.resolve()}:/workspace:rw",
            "-w",
            str(cwd),
            self.image,
            *action.argv,
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=timeout,
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
