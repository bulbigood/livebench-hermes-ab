import json
from pathlib import Path
from types import MappingProxyType

import pytest

from livebench_hermes_ab.artifacts import (
    ExecutionBundle,
    FilesystemArtifactStore,
    parse_cell_outcome_bytes,
    serialize_cell_outcome,
)
from livebench_hermes_ab.domain import (
    CellId,
    ExcludedOutcome,
    ExclusionCode,
    PersistenceError,
    UnsupportedSchemaVersion,
    ValidOutcome,
)
from livebench_hermes_ab.resume import ResumePolicy, plan_resume


def test_cell_schema_round_trip_and_old_schema_rejected() -> None:
    outcome = ValidOutcome(CellId("base", "pair", "q", 1), {"answer": "yes"}, 2.0)
    assert parse_cell_outcome_bytes(serialize_cell_outcome(outcome)) == outcome
    with pytest.raises(UnsupportedSchemaVersion):
        parse_cell_outcome_bytes(b'{"cell_journal_schema_version":1}')


def test_excluded_outcome_round_trip_preserves_structured_evidence() -> None:
    outcome = ExcludedOutcome(
        CellId("moa", "pair", "q", 1),
        ExclusionCode.INVALID_MOA_TRACE,
        "bad trace",
        2.0,
        {"provider_calls": [{"role": "reference", "usage_complete": False}]},
    )

    parsed = parse_cell_outcome_bytes(serialize_cell_outcome(outcome))

    assert isinstance(parsed, ExcludedOutcome)
    assert parsed.evidence == {
        "provider_calls": [{"role": "reference", "usage_complete": False}]
    }


def test_cell_schema_serializes_deeply_immutable_evidence() -> None:
    outcome = ValidOutcome(
        CellId("base", "pair", "q", 1),
        MappingProxyType(
            {
                "answer": "yes",
                "trace_audit": (
                    MappingProxyType({"references": (("provider", "model"),)}),
                ),
            }
        ),
        2.0,
    )

    value = json.loads(serialize_cell_outcome(outcome))

    assert value["answer_record"] == {
        "answer": "yes",
        "trace_audit": [{"references": [["provider", "model"]]}],
    }


def test_retry_plan_preserves_authoritative_outcome_until_promotion(tmp_path: Path) -> None:
    cell = CellId("base", "pair", "q", 1)
    old = ExcludedOutcome(cell, ExclusionCode.CELL_TIMEOUT, "old", 1.0)
    store = FilesystemArtifactStore(tmp_path)
    store.promote_cell_outcome(old)
    plan = plan_resume((old,), (cell,), ResumePolicy(2, frozenset({ExclusionCode.CELL_TIMEOUT})))
    assert plan.cells == (cell,)
    assert store.load_cell_outcomes() == (old,)
    new = ValidOutcome(cell, {"answer": "new"}, 1.0)
    store.write_cell_attempt(plan.attempts[0], new)
    attempt = next((tmp_path / "attempts").glob("*.json"))
    attempt_value = json.loads(attempt.read_text())
    assert attempt_value == {
        "attempt_schema_version": 1,
        "outcome": json.loads(serialize_cell_outcome(new)),
    }
    with pytest.raises(PersistenceError, match="already exists"):
        store.write_cell_attempt(plan.attempts[0], new)
    assert store.load_cell_outcomes() == (old,)
    store.promote_cell_outcome(new)
    assert store.load_cell_outcomes() == (new,)
    assert len(tuple((tmp_path / "attempts").glob("*.json"))) == 1


def test_failed_generation_leaves_previous_pointer_authoritative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cell = CellId("base", "pair", "q", 1)
    old = ValidOutcome(cell, {"answer": "old"}, 1.0)
    store = FilesystemArtifactStore(tmp_path)
    store.publish_execution(ExecutionBundle((old,)))
    previous = store.current_generation("execution")
    original = store._atomic_file

    def fail_pointer(path: Path, data: bytes) -> None:
        if path.name == "execution.current":
            raise OSError("injected pointer failure")
        original(path, data)

    monkeypatch.setattr(store, "_atomic_file", fail_pointer)
    with pytest.raises(PersistenceError, match="failed to publish execution generation"):
        store.publish_execution(ExecutionBundle((ValidOutcome(cell, {"answer": "new"}, 2.0),)))
    assert store.current_generation("execution") == previous


def test_committed_execution_detects_generation_and_journal_tampering(tmp_path: Path) -> None:
    cell = CellId("base", "pair", "q", 0)
    outcome = ValidOutcome(cell, {"answer": "old"}, 1.0)
    store = FilesystemArtifactStore(tmp_path)
    store.promote_cell_outcome(outcome)
    store.publish_execution(ExecutionBundle((outcome,)))
    assert store.load_committed_execution() == (outcome,)

    newer = ValidOutcome(cell, {"answer": "new"}, 1.0)
    store.promote_cell_outcome(newer)
    with pytest.raises(Exception, match="journals differ"):
        store.load_committed_execution()
    store.promote_cell_outcome(outcome)

    generation = store.current_generation("execution")
    assert generation is not None
    (generation / "outcomes.jsonl").write_bytes(b"tampered\n")
    with pytest.raises(Exception, match="digest mismatch"):
        store.load_committed_execution()
