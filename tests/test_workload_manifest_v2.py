import json
from pathlib import Path

import pytest
import yaml

from livebench_hermes_ab.config import SelectionConfig, load_config
from livebench_hermes_ab.domain import (
    ConfigError,
    IntegrityError,
    ManifestError,
    UnsupportedSchemaVersion,
)
from livebench_hermes_ab.manifest import (
    CompatibilityResult,
    Provenance,
    build_manifest,
    parse_manifest,
    serialize_manifest,
    verify_frozen_artifacts,
)
from livebench_hermes_ab.scoring_adapters import objective_score, registry
from livebench_hermes_ab.workload import Question, build_workload, select_questions


def _plain(value):
    if hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def test_workload_and_manifest_are_ordered_and_versioned() -> None:
    config = load_config(Path("config.yaml"))
    questions = tuple(
        Question(spec["id"], category, spec["family"], (f"prompt {spec['id']}",), {})
        for category, specs in config.selection.scenarios.items()
        for spec in specs
    )
    workload = build_workload(
        questions, config.arms, config.generation.samples_per_task, config.seed
    )
    assert len(workload.cells) == 600
    assert workload.expected_provider_calls == 900
    manifest = build_manifest(
        config,
        workload,
        Provenance(config.upstream_commit),
        CompatibilityResult("0.19.1", True, None),
    )
    assert parse_manifest(serialize_manifest(manifest)) == manifest
    assert manifest.arm_order == ("base", "gpt_medium", "moa_minimax", "moa_mimo")


def test_old_manifest_fails_closed() -> None:
    with pytest.raises(UnsupportedSchemaVersion, match="schema version 2"):
        parse_manifest({"manifest_schema_version": 1})


def test_selection_rejects_question_released_after_experiment() -> None:
    question = Question(
        "q",
        "reasoning",
        "spatial",
        ("prompt",),
        {"livebench_release_date": "2026-07-01", "livebench_removal_date": ""},
    )
    config = SelectionConfig({"reasoning": ({"id": "q", "family": "spatial"},)})

    with pytest.raises(ConfigError, match="not active for release 2026-06-25"):
        select_questions((question,), config, "2026-06-25")


def test_selection_rejects_question_removed_on_experiment_release() -> None:
    question = Question(
        "q",
        "reasoning",
        "spatial",
        ("prompt",),
        {"livebench_release_date": "2025-01-01", "livebench_removal_date": "2026-06-25"},
    )
    config = SelectionConfig({"reasoning": ({"id": "q", "family": "spatial"},)})

    with pytest.raises(ConfigError, match="not active for release 2026-06-25"):
        select_questions((question,), config, "2026-06-25")


def test_scoring_registry_rejects_unsupported_tasks_before_paid_execution() -> None:
    with pytest.raises(IntegrityError, match="unsupported objective scoring tasks: unknown"):
        registry({"unknown"})


def test_scoring_registry_supports_deterministic_replacement_families() -> None:
    tasks = {"math_comp", "olympiad", "cta", "connections"}
    assert set(registry(tasks)) == tasks


def test_replacement_family_scorers_accept_known_ground_truth() -> None:
    import json

    paths = {
        "math_comp": Path("data/live_bench/math/math_comp/question.jsonl"),
        "olympiad": Path("data/live_bench/math/olympiad/question.jsonl"),
        "cta": Path("data/live_bench/data_analysis/cta/question.jsonl"),
        "connections": Path("data/live_bench/language/connections/question.jsonl"),
    }
    for task, path in paths.items():
        question = json.loads(path.read_text().splitlines()[0])
        truth = str(question["ground_truth"])
        if task == "math_comp":
            answer = truth
        elif task == "olympiad":
            answer = f"Answer: {truth}"
        elif task == "connections":
            answer = f"<solution>{truth}</solution>"
        else:
            answer = truth
        assert objective_score(question, answer) == 1.0


def test_manifest_rejects_invalid_matrix_and_frozen_artifact_drift(tmp_path: Path) -> None:
    config = load_config(Path("config.yaml"))
    question = Question("q", "reasoning", "spatial", ("one", "two"), {})
    workload = build_workload((question,), config.arms, 1, 1)
    frozen = {
        "config.snapshot.yaml": b"config\n",
        "questions.json": b"questions\n",
        **{
            f"homes/{arm.name}/config.yaml": yaml.safe_dump(
                _plain(arm.hermes), sort_keys=False
            ).encode()
            for arm in config.arms
        },
    }
    manifest = build_manifest(
        config,
        workload,
        Provenance(config.upstream_commit),
        CompatibilityResult("0.19.1", True, None),
        frozen_files=frozen,
    )
    for name in manifest.frozen_file_sha256:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(frozen[name])
    verify_frozen_artifacts(tmp_path, manifest)
    (tmp_path / "questions.json").write_bytes(b"corrupt")
    with pytest.raises(IntegrityError, match="questions.json"):
        verify_frozen_artifacts(tmp_path, manifest)

    value = json.loads(serialize_manifest(manifest))
    value["arm_order"].append(value["arm_order"][0])
    with pytest.raises(ManifestError):
        parse_manifest(value)
