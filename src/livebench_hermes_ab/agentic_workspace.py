from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class PatchExtractionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CandidatePatch:
    content: bytes
    sha256: str
    paths: tuple[str, ...]
    removed_paths: tuple[str, ...] = ()


_HEADER = re.compile(rb"^diff --git a/(.+?) b/(.+?)$")


def _sections(content: bytes) -> tuple[tuple[str, bytes], ...]:
    lines = content.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith(b"diff --git ")]
    if not starts:
        raise PatchExtractionError("candidate patch is empty or not a supported unified Git diff")
    sections = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        header = lines[start].rstrip(b"\r\n")
        match = _HEADER.match(header)
        if match is None or match.group(1) != match.group(2):
            raise PatchExtractionError("renames and non-canonical Git diff headers are unsupported")
        path = match.group(2).decode("utf-8", errors="strict")
        sections.append((path, b"".join(lines[start:end])))
    return tuple(sections)


def _candidate(content: bytes, removed: tuple[str, ...] = ()) -> CandidatePatch:
    sections = _sections(content)
    return CandidatePatch(
        content,
        hashlib.sha256(content).hexdigest(),
        tuple(path for path, _ in sections),
        removed,
    )


def extract_candidate_patch(workspace: Path, base_sha: str) -> CandidatePatch:
    if not (workspace / ".git").exists():
        raise PatchExtractionError("workspace is not a Git repository")
    completed = subprocess.run(
        ["git", "-C", str(workspace), "-c", "core.fileMode=false", "diff", "--binary", base_sha],
        check=True,
        capture_output=True,
    )
    if not completed.stdout.strip():
        raise PatchExtractionError("candidate patch is empty")
    return _candidate(completed.stdout)


def filter_hidden_test_changes(content: bytes, hidden_paths: tuple[str, ...]) -> CandidatePatch:
    hidden = set(hidden_paths)
    kept = []
    removed = []
    for path, section in _sections(content):
        if path in hidden:
            removed.append(path)
        else:
            kept.append((path, section))
    if not kept:
        raise PatchExtractionError("candidate patch contains only hidden-test changes")
    filtered = b"".join(section for _, section in kept)
    return _candidate(filtered, tuple(sorted(removed)))
