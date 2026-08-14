from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from livebench_hermes_ab.domain import CellId, CellSpec, ConfigError, IntegrityError
from livebench_hermes_ab.extension import (
    extended_config_bytes,
    import_extension_artifacts,
    validate_manifest_extension,
)
from livebench_hermes_ab.manifest import CompatibilityResult, Provenance, RunManifest


def _manifest(cells: tuple[CellSpec, ...]) -> RunManifest:
    return RunManifest(
        experiment_id="experiment",
        manifest_schema_version=2,
        arm_order=("base", "moa"),
        baseline_arm="base",
        cells=cells,
        expected_provider_calls=sum(cell.expected_provider_calls for cell in cells),
        execution_mode="streaming",
        workers=2,
        timeout_seconds=30,
        max_attempts=2,
        retryable_codes=(),
        scoring_implementation="livebench-objective-ground-truth",
        scoring_schema_version=2,
        provenance=Provenance("a" * 40),
        compatibility=CompatibilityResult("0.19.1", True, None),
        frozen_file_sha256={"questions.json": "q", "config.snapshot.yaml": "c"},
    )


def test_extended_config_changes_only_sample_count_and_requires_growth() -> None:
    source = yaml.safe_dump(
        {"experiment": {"id": "x"}, "generation": {"samples_per_task": 10}}
    ).encode()
    value, old = extended_config_bytes(source, 20)
    parsed = yaml.safe_load(value)
    assert old == 10
    assert parsed["generation"]["samples_per_task"] == 20
    assert parsed["experiment"] == {"id": "x"}
    with pytest.raises(ConfigError, match="must exceed"):
        extended_config_bytes(source, 10)


def test_manifest_extension_requires_exact_old_cell_subset() -> None:
    old_cell = CellSpec(CellId("base", "p0", "q", 0), "prompt", "base", 1)
    new_cell = CellSpec(CellId("base", "p1", "q", 1), "prompt", "base", 1)
    old = _manifest((old_cell,))
    new = _manifest((old_cell, new_cell))
    validate_manifest_extension(old, new)
    changed = replace(new, cells=(replace(old_cell, prompt="changed"), new_cell))
    with pytest.raises(IntegrityError, match="changed 1 frozen cells"):
        validate_manifest_extension(old, changed)


def test_extension_imports_immutable_artifacts_and_writes_provenance(tmp_path: Path) -> None:
    source = tmp_path / "old"
    output = tmp_path / "new"
    (source / "cells").mkdir(parents=True)
    (source / "attempts").mkdir()
    output.mkdir()
    (source / "manifest.json").write_text("manifest\n")
    (source / "cells" / "cell.json").write_text("cell\n")
    (source / "attempts" / "attempt.json").write_text("attempt\n")

    value = import_extension_artifacts(source, output, old_samples=10, new_samples=20)

    assert value["imported_cells"] == 1
    assert (output / "cells" / "cell.json").read_bytes() == b"cell\n"
    assert (output / "extension.json").is_file()
