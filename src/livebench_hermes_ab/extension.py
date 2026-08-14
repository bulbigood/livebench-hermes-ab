from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import yaml

from .domain import ConfigError, IntegrityError
from .manifest import RunManifest


def extended_config_bytes(snapshot: bytes, to_samples: int) -> tuple[bytes, int]:
    if isinstance(to_samples, bool) or to_samples < 1:
        raise ConfigError("extension target must be a positive sample count")
    try:
        value = yaml.safe_load(snapshot)
        generation = value["generation"]
        current = generation["samples_per_task"]
    except (TypeError, KeyError, yaml.YAMLError) as exc:
        raise ConfigError("invalid frozen config snapshot") from exc
    if isinstance(current, bool) or not isinstance(current, int) or current < 1:
        raise ConfigError("frozen samples_per_task is invalid")
    if to_samples <= current:
        raise ConfigError(
            f"extension target must exceed frozen samples_per_task ({current})"
        )
    generation["samples_per_task"] = to_samples
    return yaml.safe_dump(value, sort_keys=False).encode(), current


def validate_manifest_extension(old: RunManifest, new: RunManifest) -> None:
    invariant_old = replace(
        old,
        cells=(),
        expected_provider_calls=0,
        frozen_file_sha256={},
    )
    invariant_new = replace(
        new,
        cells=(),
        expected_provider_calls=0,
        frozen_file_sha256={},
    )
    if invariant_old != invariant_new:
        raise IntegrityError("extension changed frozen run invariants")
    old_hashes = {
        name: digest
        for name, digest in old.frozen_file_sha256.items()
        if name != "config.snapshot.yaml"
    }
    new_hashes = {
        name: digest
        for name, digest in new.frozen_file_sha256.items()
        if name != "config.snapshot.yaml"
    }
    if old_hashes != new_hashes:
        raise IntegrityError("extension frozen evidence differs")
    old_by_id = {cell.id: cell for cell in old.cells}
    new_by_id = {cell.id: cell for cell in new.cells}
    if len(old_by_id) != len(old.cells) or len(new_by_id) != len(new.cells):
        raise IntegrityError("extension manifest contains duplicate cells")
    if not old_by_id.keys() < new_by_id.keys():
        raise IntegrityError("extension must strictly add cells")
    changed = [cell_id for cell_id, cell in old_by_id.items() if new_by_id[cell_id] != cell]
    if changed:
        raise IntegrityError(f"extension changed {len(changed)} frozen cells")


def import_extension_artifacts(
    source_run: Path,
    output_run: Path,
    *,
    old_samples: int,
    new_samples: int,
) -> dict[str, object]:
    imported: dict[str, int] = {}
    for directory in ("cells", "attempts"):
        source = source_run / directory
        target = output_run / directory
        target.mkdir(parents=True, exist_ok=True)
        count = 0
        for item in sorted(source.glob("*.json")):
            destination = target / item.name
            if destination.exists():
                raise IntegrityError(f"extension destination already contains {item.name}")
            shutil.copy2(item, destination)
            if hashlib.sha256(item.read_bytes()).digest() != hashlib.sha256(
                destination.read_bytes()
            ).digest():
                raise IntegrityError(f"extension copy digest mismatch: {item.name}")
            count += 1
        imported[directory] = count
    provenance = {
        "extension_schema_version": 1,
        "source_run": str(source_run.resolve()),
        "source_manifest_sha256": hashlib.sha256(
            (source_run / "manifest.json").read_bytes()
        ).hexdigest(),
        "old_samples_per_task": old_samples,
        "new_samples_per_task": new_samples,
        "imported_cells": imported["cells"],
        "imported_attempts": imported["attempts"],
    }
    (output_run / "extension.json").write_text(
        json.dumps(provenance, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return provenance
