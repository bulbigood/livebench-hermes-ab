from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .domain import (
    AttemptDiagnostic,
    CellId,
    CellOutcome,
    ExcludedOutcome,
    ExclusionCode,
    IntegrityError,
    PersistenceError,
    UnsupportedSchemaVersion,
    ValidOutcome,
)
from .manifest import RunManifest, parse_manifest, serialize_manifest

CELL_JOURNAL_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class ExecutionBundle:
    outcomes: tuple[CellOutcome, ...]


@dataclass(frozen=True, slots=True)
class ScoringBundle:
    files: Mapping[Path, bytes]


class ArtifactStore(Protocol):
    def write_cell_attempt(
        self, attempt: int, outcome: CellOutcome, diagnostic: AttemptDiagnostic | None = None
    ) -> None: ...
    def promote_cell_outcome(self, outcome: CellOutcome) -> None: ...
    def load_cell_outcomes(self) -> tuple[CellOutcome, ...]: ...
    def load_attempt_outcomes(self) -> tuple[CellOutcome, ...]: ...
    def publish_execution(self, bundle: ExecutionBundle) -> None: ...
    def publish_scoring(self, bundle: ScoringBundle) -> None: ...
    def attempt_numbers(self, cell: CellId) -> tuple[int, ...]: ...


def _cell_value(cell: CellId) -> dict[str, object]:
    return {
        "arm": cell.arm,
        "pair_id": cell.pair_id,
        "question_id": cell.question_id,
        "sample_index": cell.sample_index,
    }


def _plain_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain_json_value(child) for child in value]
    return value


def serialize_cell_outcome(value: CellOutcome) -> bytes:
    data: dict[str, object] = {
        "cell_journal_schema_version": 2,
        "cell": _cell_value(value.cell),
        "elapsed_seconds": value.elapsed_seconds,
    }
    if isinstance(value, ValidOutcome):
        data.update({"status": "valid", "answer_record": _plain_json_value(value.answer_record)})
    else:
        data.update({"status": "excluded", "code": value.code.value, "reason": value.reason})
        if value.evidence is not None:
            data["evidence"] = _plain_json_value(value.evidence)
    return (
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    )


def parse_cell_outcome_bytes(value: bytes) -> CellOutcome:
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise IntegrityError("invalid cell outcome JSON") from exc
    if data.get("cell_journal_schema_version") != 2:
        raise UnsupportedSchemaVersion("cell journal schema version 2 is required")
    try:
        status = data["status"]
        expected = {"cell_journal_schema_version", "cell", "elapsed_seconds", "status"}
        expected |= {"answer_record"} if status == "valid" else {"code", "reason"}
        allowed = expected | ({"evidence"} if status == "excluded" else set())
        if not expected <= set(data) or not set(data) <= allowed:
            raise IntegrityError("cell outcome keys differ")
        raw = data["cell"]
        if set(raw) != {"arm", "pair_id", "question_id", "sample_index"}:
            raise IntegrityError("cell identity keys differ")
        cell = CellId(
            str(raw["arm"]), str(raw["pair_id"]), str(raw["question_id"]), int(raw["sample_index"])
        )
        elapsed = data["elapsed_seconds"]
        if cell.sample_index < 0 or not all((cell.arm, cell.pair_id, cell.question_id)):
            raise IntegrityError("invalid cell identity")
        if status == "valid":
            return ValidOutcome(cell, data["answer_record"], float(elapsed))
        if status == "excluded":
            return ExcludedOutcome(
                cell,
                ExclusionCode(data["code"]),
                str(data["reason"]),
                None if elapsed is None else float(elapsed),
                data.get("evidence"),
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError("invalid cell outcome") from exc
    raise IntegrityError("invalid cell outcome status")


def parse_manifest_bytes(value: bytes) -> RunManifest:
    return parse_manifest(value)


def serialize_scoring_bundle(value: ScoringBundle) -> Mapping[Path, bytes]:
    return value.files


class FilesystemArtifactStore:
    def __init__(self, root: Path):
        self.root = root

    @staticmethod
    def _key(cell: CellId) -> str:
        readable = f"{cell.arm}-{cell.pair_id}-{cell.sample_index}"
        return readable.replace("/", "_")

    def _atomic_file(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError as exc:
            try:
                os.unlink(name)
            except OSError:
                pass
            raise PersistenceError(f"failed to publish {path}") from exc

    def write_manifest(self, manifest: RunManifest) -> None:
        self._atomic_file(self.root / "manifest.json", serialize_manifest(manifest))

    def write_cell_attempt(
        self, attempt: int, outcome: CellOutcome, diagnostic: AttemptDiagnostic | None = None
    ) -> None:
        if attempt < 1:
            raise PersistenceError("attempt number must be positive")
        path = self.root / "attempts" / f"{self._key(outcome.cell)}-attempt-{attempt}.json"
        if path.exists():
            raise PersistenceError(f"attempt artifact already exists: {path.name}")
        value: dict[str, object] = {
            "attempt_schema_version": 1,
            "outcome": json.loads(serialize_cell_outcome(outcome)),
        }
        if diagnostic is not None:
            value["diagnostic"] = {
                "kind": diagnostic.kind,
                "encoding": diagnostic.encoding,
                "content": diagnostic.content,
            }
        self._atomic_file(
            path,
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            + b"\n",
        )

    def promote_cell_outcome(self, outcome: CellOutcome) -> None:
        self._atomic_file(
            self.root / "cells" / f"{self._key(outcome.cell)}.json", serialize_cell_outcome(outcome)
        )

    def load_cell_outcomes(self) -> tuple[CellOutcome, ...]:
        path = self.root / "cells"
        return (
            tuple(parse_cell_outcome_bytes(p.read_bytes()) for p in sorted(path.glob("*.json")))
            if path.exists()
            else ()
        )

    def attempt_numbers(self, cell: CellId) -> tuple[int, ...]:
        prefix = f"{self._key(cell)}-attempt-"
        numbers = []
        for path in (self.root / "attempts").glob(f"{prefix}*.json"):
            try:
                numbers.append(int(path.stem.removeprefix(prefix)))
            except ValueError as exc:
                raise IntegrityError(f"malformed attempt artifact: {path.name}") from exc
        return tuple(sorted(numbers))

    def load_attempt_outcomes(self) -> tuple[CellOutcome, ...]:
        outcomes: list[CellOutcome] = []
        for path in sorted((self.root / "attempts").glob("*.json")):
            try:
                value = json.loads(path.read_bytes())
                if value.get("attempt_schema_version") != 1 or "outcome" not in value:
                    raise IntegrityError(f"invalid attempt artifact: {path.name}")
                encoded = (
                    json.dumps(
                        value["outcome"],
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode()
                    + b"\n"
                )
                outcomes.append(parse_cell_outcome_bytes(encoded))
            except json.JSONDecodeError as exc:
                raise IntegrityError(f"invalid attempt artifact: {path.name}") from exc
        return tuple(outcomes)

    def _publish_generation(self, kind: str, files: Mapping[Path, bytes]) -> None:
        generation = uuid.uuid4().hex
        stage = self.root / ".staging" / f"{kind}-{generation}"
        target = self.root / "generations" / kind / generation
        try:
            for relative, data in files.items():
                if relative.is_absolute() or ".." in relative.parts:
                    raise PersistenceError("bundle path escapes generation")
                self._atomic_file(stage / relative, data)
            digest = hashlib.sha256(
                b"".join(path.read_bytes() for path in sorted(stage.rglob("*")) if path.is_file())
            ).hexdigest()
            self._atomic_file(
                stage / "generation.json",
                json.dumps({"schema_version": 2, "sha256": digest}, sort_keys=True).encode()
                + b"\n",
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage, target)
            self._atomic_file(self.root / f"{kind}.current", (generation + "\n").encode())
        except (OSError, PersistenceError) as exc:
            shutil.rmtree(stage, ignore_errors=True)
            raise PersistenceError(f"failed to publish {kind} generation") from exc

    def publish_execution(self, bundle: ExecutionBundle) -> None:
        rows = b"".join(serialize_cell_outcome(outcome) for outcome in bundle.outcomes)
        self._publish_generation("execution", {Path("outcomes.jsonl"): rows})

    def publish_scoring(self, bundle: ScoringBundle) -> None:
        self._publish_generation("scoring", bundle.files)

    def current_generation(self, kind: str) -> Path | None:
        pointer = self.root / f"{kind}.current"
        if not pointer.exists():
            return None
        path = self.root / "generations" / kind / pointer.read_text().strip()
        if not (path / "generation.json").exists():
            raise IntegrityError(f"incomplete {kind} generation")
        try:
            metadata = json.loads((path / "generation.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IntegrityError(f"invalid {kind} generation metadata") from exc
        if set(metadata) != {"schema_version", "sha256"} or metadata["schema_version"] != 2:
            raise IntegrityError(f"invalid {kind} generation metadata")
        digest = hashlib.sha256(
            b"".join(
                item.read_bytes()
                for item in sorted(path.rglob("*"))
                if item.is_file() and item.name != "generation.json"
            )
        ).hexdigest()
        if digest != metadata["sha256"]:
            raise IntegrityError(f"{kind} generation digest mismatch")
        return path

    def load_committed_execution(self) -> tuple[CellOutcome, ...]:
        generation = self.current_generation("execution")
        if generation is None:
            raise IntegrityError("execution is not complete")
        path = generation / "outcomes.jsonl"
        outcomes = tuple(
            parse_cell_outcome_bytes(line + b"\n")
            for line in path.read_bytes().splitlines()
            if line.strip()
        )
        if outcomes != self.load_cell_outcomes():
            raise IntegrityError("cell journals differ from committed execution evidence")
        return outcomes
