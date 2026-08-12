from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .domain import HarnessExecutionError


@dataclass(frozen=True, slots=True)
class HermesRequest:
    prompt: str
    profile: str
    timeout_seconds: int
    home: Path | None


@dataclass(frozen=True, slots=True)
class HermesResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    trace_bytes: bytes | None


class HermesRunner(Protocol):
    def invoke(self, request: HermesRequest) -> HermesResult: ...


def subprocess_environment(home: Path) -> dict[str, str]:
    secret_markers = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    environment = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in secret_markers)
    }
    environment["HERMES_HOME"] = str(home)
    return environment


def resolve_hermes_executable(explicit: str | Path | None = None) -> str:
    if explicit:
        path = shutil.which(str(explicit))
    else:
        path = shutil.which("hermes")
    if not path:
        raise HarnessExecutionError("Hermes executable not found")
    return path


def build_command(request: HermesRequest, executable: str) -> list[str]:
    return [executable, "--ignore-rules", "--oneshot", request.prompt]


class SubprocessHermesRunner:
    def __init__(self, executable: str):
        self.executable = executable

    def invoke(self, request: HermesRequest) -> HermesResult:
        import time

        if request.home is None:
            raise HarnessExecutionError("isolated Hermes home is required")
        environment = subprocess_environment(request.home)
        trace_root = request.home / "moa-traces"
        before = {
            path: (path.stat().st_size, path.stat().st_mtime_ns)
            for path in trace_root.glob("*.jsonl")
        }
        started = time.monotonic()
        try:
            process = subprocess.run(
                build_command(request, self.executable),
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                env=environment,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return HermesResult(124, "", "cell timeout", time.monotonic() - started, None)
        except OSError as exc:
            raise HarnessExecutionError(f"cannot invoke Hermes: {exc}") from exc
        changed = [
            path
            for path in trace_root.glob("*.jsonl")
            if path not in before or (path.stat().st_size, path.stat().st_mtime_ns) != before[path]
        ]
        trace_bytes = None
        if len(changed) == 1:
            path = changed[0]
            data = path.read_bytes()
            if path in before and len(data) >= before[path][0]:
                data = data[before[path][0] :]
            trace_bytes = data
        return HermesResult(
            process.returncode,
            process.stdout,
            process.stderr,
            time.monotonic() - started,
            trace_bytes,
        )


def probe_compatibility(executable: str, expected: str) -> tuple[str, bool, str | None]:
    try:
        process = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessExecutionError(f"Hermes compatibility probe failed: {exc}") from exc
    if process.returncode:
        raise HarnessExecutionError("Hermes compatibility probe failed")
    match = re.search(r"\d+\.\d+\.\d+", process.stdout + process.stderr)
    if not match:
        raise HarnessExecutionError("could not parse Hermes version")
    version = match.group(0)
    verified = version == expected
    return (
        version,
        verified,
        None if verified else f"unverified Hermes version {version}; expected {expected}",
    )
