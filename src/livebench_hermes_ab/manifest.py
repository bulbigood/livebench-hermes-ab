from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

from .config import ExperimentConfig
from .domain import (
    CellId,
    CellSpec,
    ExclusionCode,
    IntegrityError,
    ManifestError,
    UnsupportedSchemaVersion,
)
from .workload import WorkloadPlan

MANIFEST_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class Provenance:
    upstream_commit: str


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    installed_version: str
    verified: bool
    warning: str | None


@dataclass(frozen=True, slots=True)
class RunManifest:
    experiment_id: str
    manifest_schema_version: int
    arm_order: tuple[str, ...]
    baseline_arm: str
    cells: tuple[CellSpec, ...]
    expected_provider_calls: int
    execution_mode: str
    workers: int | str
    timeout_seconds: int
    max_attempts: int
    retryable_codes: tuple[str, ...]
    scoring_implementation: str
    scoring_schema_version: int
    provenance: Provenance
    compatibility: CompatibilityResult
    frozen_file_sha256: Mapping[str, str]


def build_manifest(
    config: ExperimentConfig,
    workload: WorkloadPlan,
    provenance: Provenance,
    compatibility: CompatibilityResult,
    frozen_files: Mapping[str, bytes] | None = None,
) -> RunManifest:
    if workload.arm_order != tuple(arm.name for arm in config.arms):
        raise ManifestError("workload arm order differs from config")
    if frozen_files is None:
        frozen_files = {
            "config.snapshot.yaml": b"",
            "questions.json": b"",
            **{f"homes/{arm}/config.yaml": b"" for arm in workload.arm_order},
        }
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in frozen_files.items()}
    manifest = RunManifest(
        config.experiment_id,
        2,
        workload.arm_order,
        config.baseline_arm,
        workload.cells,
        workload.expected_provider_calls,
        config.execution.mode,
        config.execution.workers,
        config.execution.timeout_seconds,
        config.generation.retry.max_attempts,
        tuple(sorted(code.value for code in config.generation.retry.retryable_codes)),
        config.scoring.implementation,
        config.scoring.schema_version,
        provenance,
        compatibility,
        MappingProxyType(hashes),
    )
    _validate_manifest(manifest)
    return manifest


def manifest_value(value: RunManifest) -> dict[str, object]:
    return {
        "manifest_schema_version": 2,
        "experiment_id": value.experiment_id,
        "arm_order": list(value.arm_order),
        "baseline_arm": value.baseline_arm,
        "cells": [
            {
                "arm": c.id.arm,
                "pair_id": c.id.pair_id,
                "question_id": c.id.question_id,
                "sample_index": c.id.sample_index,
                "prompt": c.prompt,
                "hermes_profile": c.hermes_profile,
                "expected_provider_calls": c.expected_provider_calls,
                "turns": list(c.turns),
                "system_prompt": c.system_prompt,
            }
            for c in value.cells
        ],
        "expected_provider_calls": value.expected_provider_calls,
        "execution": {
            "mode": value.execution_mode,
            "workers": value.workers,
            "timeout_seconds": value.timeout_seconds,
        },
        "retry": {
            "max_attempts": value.max_attempts,
            "retryable_codes": list(value.retryable_codes),
        },
        "scoring": {
            "implementation": value.scoring_implementation,
            "schema_version": value.scoring_schema_version,
        },
        "provenance": {"upstream_commit": value.provenance.upstream_commit},
        "compatibility": {
            "installed_version": value.compatibility.installed_version,
            "verified": value.compatibility.verified,
            "warning": value.compatibility.warning,
        },
        "frozen_file_sha256": dict(value.frozen_file_sha256),
    }


def serialize_manifest(value: RunManifest) -> bytes:
    return (
        json.dumps(
            manifest_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        + b"\n"
    )


def _parse_cells(raw_cells: object) -> tuple[CellSpec, ...]:
    cell_keys = {
        "arm",
        "pair_id",
        "question_id",
        "sample_index",
        "prompt",
        "hermes_profile",
        "expected_provider_calls",
        "turns",
        "system_prompt",
    }
    parsed = []
    for cell in raw_cells:  # type: ignore[union-attr]
        if not isinstance(cell, Mapping) or set(cell) != cell_keys:
            raise ManifestError("invalid cell keys")
        parsed.append(
            CellSpec(
                CellId(
                    str(cell["arm"]),
                    str(cell["pair_id"]),
                    str(cell["question_id"]),
                    int(cell["sample_index"]),
                ),
                str(cell["prompt"]),
                str(cell["hermes_profile"]),
                int(cell["expected_provider_calls"]),
                tuple(str(turn) for turn in cell["turns"]),
                None if cell["system_prompt"] is None else str(cell["system_prompt"]),
            )
        )
    return tuple(parsed)


def _require_nested_keys(items: tuple[tuple[object, set[str]], ...]) -> None:
    if any(not isinstance(item, Mapping) or set(item) != keys for item, keys in items):
        raise ManifestError("invalid nested manifest keys")


def parse_manifest(value: object) -> RunManifest:
    if isinstance(value, bytes):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ManifestError("invalid manifest JSON") from exc
    if not isinstance(value, Mapping):
        raise ManifestError("manifest must be an object")
    if value.get("manifest_schema_version") != 2:
        raise UnsupportedSchemaVersion("manifest schema version 2 is required")
    required = {
        "manifest_schema_version",
        "experiment_id",
        "arm_order",
        "baseline_arm",
        "cells",
        "expected_provider_calls",
        "execution",
        "retry",
        "scoring",
        "provenance",
        "compatibility",
        "frozen_file_sha256",
    }
    if set(value) != required:
        raise ManifestError(f"manifest keys differ: {sorted(set(value) ^ required)}")
    try:
        arm_order = tuple(value["arm_order"])
        cells = _parse_cells(value["cells"])
        if not arm_order or {c.id.arm for c in cells} != set(arm_order):
            raise ManifestError("arm_order must exactly match cell arms")
        execution, retry, scoring = value["execution"], value["retry"], value["scoring"]
        provenance, compatibility = value["provenance"], value["compatibility"]
        _require_nested_keys(
            (
                (execution, {"mode", "workers", "timeout_seconds"}),
                (retry, {"max_attempts", "retryable_codes"}),
                (scoring, {"implementation", "schema_version"}),
                (provenance, {"upstream_commit"}),
                (compatibility, {"installed_version", "verified", "warning"}),
            )
        )
        if scoring["schema_version"] != 2:
            raise UnsupportedSchemaVersion("scoring schema version 2 is required")
        manifest = RunManifest(
            str(value["experiment_id"]),
            2,
            arm_order,
            str(value["baseline_arm"]),
            cells,
            int(value["expected_provider_calls"]),
            str(execution["mode"]),
            execution["workers"],
            int(execution["timeout_seconds"]),
            int(retry["max_attempts"]),
            tuple(retry["retryable_codes"]),
            str(scoring["implementation"]),
            2,
            Provenance(str(provenance["upstream_commit"])),
            CompatibilityResult(
                str(compatibility["installed_version"]),
                bool(compatibility["verified"]),
                compatibility["warning"],
            ),
            MappingProxyType({str(k): str(v) for k, v in value["frozen_file_sha256"].items()}),
        )
        _validate_manifest(manifest)
        return manifest
    except (KeyError, TypeError, ValueError) as exc:
        raise ManifestError("invalid manifest structure") from exc


def _validate_manifest(value: RunManifest) -> None:
    if not value.arm_order or len(set(value.arm_order)) != len(value.arm_order):
        raise ManifestError("arm_order must contain unique arms")
    if value.baseline_arm not in value.arm_order:
        raise ManifestError("baseline arm must belong to arm_order")
    if value.execution_mode not in {"streaming", "balanced_waves"}:
        raise ManifestError("unsupported execution mode")
    if value.workers != "auto" and (
        isinstance(value.workers, bool) or not isinstance(value.workers, int) or value.workers < 1
    ):
        raise ManifestError("workers must be positive or auto")
    if value.execution_mode == "balanced_waves":
        if value.workers == "auto":
            raise ManifestError("balanced_waves requires explicit workers")
        if value.workers % len(value.arm_order):
            raise ManifestError("balanced_waves workers must be a multiple of arm count")
    if value.timeout_seconds < 1 or value.max_attempts < 1:
        raise ManifestError("timeouts and attempts must be positive")
    supported_codes = {code.value for code in ExclusionCode}
    if (
        len(set(value.retryable_codes)) != len(value.retryable_codes)
        or not set(value.retryable_codes) <= supported_codes
    ):
        raise ManifestError("unsupported or duplicate retry code")
    if (
        value.scoring_implementation != "livebench-objective-ground-truth"
        or value.scoring_schema_version != 2
    ):
        raise ManifestError("unsupported scoring contract")
    identities = [cell.id for cell in value.cells]
    if len(set(identities)) != len(identities):
        raise ManifestError("duplicate cell identity")
    pairs: dict[str, list[CellSpec]] = {}
    for cell in value.cells:
        if (
            cell.id.arm not in value.arm_order
            or cell.hermes_profile != cell.id.arm
            or cell.id.sample_index < 1
            or cell.expected_provider_calls < 1
        ):
            raise ManifestError("invalid cell invariant")
        if cell.turns and (not all(turn.strip() for turn in cell.turns)):
            raise ManifestError("cell turns must be non-empty")
        pairs.setdefault(cell.id.pair_id, []).append(cell)
    for cells in pairs.values():
        if {cell.id.arm for cell in cells} != set(value.arm_order) or len(cells) != len(
            value.arm_order
        ):
            raise ManifestError("incomplete cell matrix")
        if len({(cell.id.question_id, cell.id.sample_index) for cell in cells}) != 1:
            raise ManifestError("pair identity is inconsistent")
    if sum(cell.expected_provider_calls for cell in value.cells) != value.expected_provider_calls:
        raise ManifestError("expected_provider_calls does not match cells")
    expected_names = {
        "config.snapshot.yaml",
        "questions.json",
        *(f"homes/{arm}/config.yaml" for arm in value.arm_order),
    }
    if set(value.frozen_file_sha256) != expected_names or any(
        len(digest) != 64 for digest in value.frozen_file_sha256.values()
    ):
        raise ManifestError("invalid frozen artifact hashes")


def verify_frozen_artifacts(root: Path, manifest: RunManifest) -> None:
    expected_names = {
        "config.snapshot.yaml",
        "questions.json",
        *(f"homes/{arm}/config.yaml" for arm in manifest.arm_order),
    }
    if set(manifest.frozen_file_sha256) != expected_names:
        raise IntegrityError("manifest frozen artifact hash set is incomplete")
    for relative, expected in manifest.frozen_file_sha256.items():
        path = root / relative
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise IntegrityError(f"missing frozen artifact: {relative}") from exc
        if actual != expected:
            raise IntegrityError(f"frozen artifact drift: {relative}")
    calls = 0
    for arm in manifest.arm_order:
        try:
            profile = yaml.safe_load((root / f"homes/{arm}/config.yaml").read_text())
            moa = profile["moa"]
            per_turn = 1
            if moa["enabled"]:
                active = moa.get("active_preset") or moa["default_preset"]
                per_turn += len(moa["presets"][active]["reference_models"])
        except (KeyError, TypeError, OSError, yaml.YAMLError) as exc:
            raise IntegrityError(f"invalid frozen Hermes profile: {arm}") from exc
        for cell in (cell for cell in manifest.cells if cell.id.arm == arm):
            expected = per_turn * max(1, len(cell.turns))
            if cell.expected_provider_calls != expected:
                raise IntegrityError(f"provider call count drift: {cell.id}")
            calls += expected
    if calls != manifest.expected_provider_calls:
        raise IntegrityError("total provider call count drift")
