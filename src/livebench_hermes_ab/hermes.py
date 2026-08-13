from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import HermesSourceConfig
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


def _source_directory(source: HermesSourceConfig, base_directory: Path) -> Path:
    if not source.directory:
        raise HarnessExecutionError("Hermes directory source is missing")
    path = Path(source.directory).expanduser()
    return (base_directory / path).resolve() if not path.is_absolute() else path.resolve()


def verify_hermes_source(source: HermesSourceConfig, directory: Path) -> str:
    if source.mode != "git" or not source.commit:
        return str(directory.resolve())
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip()
        origin = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HarnessExecutionError(f"cannot inspect Hermes git checkout: {exc}") from exc
    if source.repository and origin.rstrip("/") != source.repository.rstrip("/"):
        raise HarnessExecutionError(
            f"Hermes repository mismatch: found {origin}; expected {source.repository}"
        )
    if head != source.commit:
        raise HarnessExecutionError(f"Hermes commit mismatch: found {head}; expected {source.commit}")
    return head


def resolve_hermes_command(
    source: HermesSourceConfig,
    base_directory: Path,
    explicit: str | Path | None = None,
) -> tuple[str, ...]:
    if explicit:
        return (resolve_hermes_executable(explicit),)
    if source.mode == "release":
        return (resolve_hermes_executable(),)
    directory = (
        _source_directory(source, base_directory)
        if source.mode == "directory"
        else base_directory
    )
    verify_hermes_source(source, directory)
    uv = shutil.which("uv")
    if (directory / "pyproject.toml").is_file() and uv:
        command = [uv, "run", "--project", str(directory)]
        if (directory / "uv.lock").is_file():
            command.append("--locked")
        return (*command, "hermes")
    for launcher in (directory / ".venv" / "bin" / "hermes", directory / "hermes"):
        if launcher.is_file() and os.access(launcher, os.X_OK):
            return (str(launcher),)
    raise HarnessExecutionError(f"Hermes executable not found in {directory}")


def materialize_git_source(source: HermesSourceConfig, destination: Path) -> Path:
    if source.mode != "git" or not source.repository or not source.commit:
        raise HarnessExecutionError("Hermes git source is incomplete")
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", "--no-checkout", source.repository, str(destination)],
                timeout=300,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise HarnessExecutionError(f"cannot clone Hermes repository: {exc}") from exc
    try:
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", source.commit],
            cwd=destination,
            timeout=300,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "--detach", source.commit],
            cwd=destination,
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HarnessExecutionError(f"cannot checkout Hermes commit: {exc}") from exc
    verify_hermes_source(source, destination)
    return destination


def build_command(request: HermesRequest, executable: tuple[str, ...]) -> list[str]:
    return [*executable, "--ignore-rules", "--oneshot", request.prompt]


class SubprocessHermesRunner:
    def __init__(self, executable: tuple[str, ...]):
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


def probe_compatibility(
    executable: tuple[str, ...], source: HermesSourceConfig
) -> tuple[str, bool, str | None]:
    try:
        process = subprocess.run(
            [*executable, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessExecutionError(f"Hermes compatibility probe failed: {exc}") from exc
    if process.returncode:
        raise HarnessExecutionError("Hermes compatibility probe failed")
    match = re.search(r"\d+\.\d+\.\d+", process.stdout + process.stderr)
    if not match:
        raise HarnessExecutionError("could not parse Hermes version")
    version = match.group(0)
    verified = source.mode != "release" or version == source.release
    return (
        version,
        verified,
        None
        if verified
        else f"unverified Hermes version {version}; expected {source.release}",
    )
