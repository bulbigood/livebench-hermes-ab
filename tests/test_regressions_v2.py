import json
from pathlib import Path

import pytest

from livebench_hermes_ab.artifacts import FilesystemArtifactStore
from livebench_hermes_ab.domain import (
    CellId,
    CellSpec,
    ExcludedOutcome,
    ExclusionCode,
    ValidOutcome,
)
from livebench_hermes_ab.execution import CellRunner
from livebench_hermes_ab.hermes import HermesRequest, HermesResult, subprocess_environment
from livebench_hermes_ab.preparation import CellWorkspaceFactory, configure_arm_homes
from livebench_hermes_ab.resume import ResumePolicy, plan_resume


class RecordingRunner:
    def __init__(self, outputs: list[str]):
        self.outputs = iter(outputs)
        self.requests: list[HermesRequest] = []

    def invoke(self, request: HermesRequest) -> HermesResult:
        self.requests.append(request)
        assert request.home is not None
        assert (request.home / "config.yaml").read_text() == "model: frozen\n"
        return HermesResult(0, next(self.outputs), "", 0.1, None)


def test_cell_workspace_clones_template_sets_home_and_cleans(tmp_path: Path) -> None:
    template = tmp_path / "homes" / "base"
    template.mkdir(parents=True)
    (template / "config.yaml").write_text("model: frozen\n")
    runner = RecordingRunner(["answer"])
    cell = CellSpec(CellId("base", "p", "q", 1), "prompt", "base", 1)

    outcome = CellRunner(runner, CellWorkspaceFactory(tmp_path)).run(cell).outcome

    assert isinstance(outcome, ValidOutcome)
    assert runner.requests[0].home is not None
    assert not runner.requests[0].home.exists()


def test_multi_turn_execution_builds_conversation_and_rejects_sentinel(tmp_path: Path) -> None:
    template = tmp_path / "homes" / "base"
    template.mkdir(parents=True)
    (template / "config.yaml").write_text("model: frozen\n")
    cell = CellSpec(
        CellId("base", "p", "q", 1),
        "System\n\nFirst",
        "base",
        2,
        turns=("First", "Second"),
        system_prompt="System",
    )
    runner = RecordingRunner(["one", "two"])
    outcome = CellRunner(runner, CellWorkspaceFactory(tmp_path)).run(cell).outcome
    assert isinstance(outcome, ValidOutcome)
    assert outcome.answer_record["turns"] == ["one", "two"]
    assert runner.requests[1].prompt == (
        "System\n\nFirst\n\nAssistant's previous response:\none\n\nSecond"
    )

    invalid = (
        CellRunner(RecordingRunner(["(empty response)"]), CellWorkspaceFactory(tmp_path))
        .run(CellSpec(CellId("base", "p2", "q2", 1), "p", "base", 1))
        .outcome
    )
    assert isinstance(invalid, ExcludedOutcome)
    assert invalid.code is ExclusionCode.INVALID_MODEL_OUTPUT


def test_arm_homes_filter_credentials_and_subprocess_secrets(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "auth.json").write_text('{"auth":true}\n')
    (source / ".env").write_text("ALLOWED_API_KEY=from-file\nOTHER_TOKEN=nope\n")
    monkeypatch.setenv("ALLOWED_API_KEY", "from-process")
    monkeypatch.setenv("UNRELATED_SECRET", "must-not-leak")
    configure_arm_homes(
        tmp_path / "homes",
        source,
        (("base", {"model": "frozen"}, ("ALLOWED_API_KEY",)),),
    )
    home = tmp_path / "homes" / "base"
    assert (home / ".env").read_text() == "ALLOWED_API_KEY=from-process\n"
    assert (home / "auth.json").resolve() == (source / "auth.json").resolve()
    environment = subprocess_environment(home)
    assert environment["HERMES_HOME"] == str(home)
    assert "UNRELATED_SECRET" not in environment
    assert "ALLOWED_API_KEY" not in environment


def test_arm_homes_accept_explicit_credentials_file(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "auth.json").write_text('{"auth":true}\n')
    (source / ".env").write_text("ALLOWED_API_KEY=wrong-default\n")
    credentials = tmp_path / "portable.env"
    credentials.write_text("ALLOWED_API_KEY=from-explicit-file\nOTHER_TOKEN=nope\n")
    monkeypatch.delenv("ALLOWED_API_KEY", raising=False)

    configure_arm_homes(
        tmp_path / "homes",
        source,
        (("base", {"model": "frozen"}, ("ALLOWED_API_KEY",)),),
        credentials_file=credentials,
    )

    assert (tmp_path / "homes" / "base" / ".env").read_text() == (
        "ALLOWED_API_KEY=from-explicit-file\n"
    )


def test_process_environment_precedes_credentials_file(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "auth.json").write_text("{}\n")
    credentials = tmp_path / "portable.env"
    credentials.write_text("ALLOWED_API_KEY=from-file\n")
    monkeypatch.setenv("ALLOWED_API_KEY", "from-process")

    configure_arm_homes(
        tmp_path / "homes",
        source,
        (("base", {"model": "frozen"}, ("ALLOWED_API_KEY",)),),
        credentials_file=credentials,
    )

    assert (tmp_path / "homes" / "base" / ".env").read_text() == ("ALLOWED_API_KEY=from-process\n")


def test_explicit_credentials_file_must_exist(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "auth.json").write_text("{}\n")

    with pytest.raises(Exception, match="credentials file missing"):
        configure_arm_homes(
            tmp_path / "homes",
            source,
            (("base", {"model": "frozen"}, ("ALLOWED_API_KEY",)),),
            credentials_file=tmp_path / "missing.env",
        )


def test_resume_uses_persisted_attempts_and_supports_third_attempt(tmp_path: Path) -> None:
    cell = CellId("base", "pair", "q", 1)
    store = FilesystemArtifactStore(tmp_path)
    old = ExcludedOutcome(cell, ExclusionCode.CELL_TIMEOUT, "old", 1.0)
    store.promote_cell_outcome(old)
    store.write_cell_attempt(1, old)
    store.write_cell_attempt(2, old)
    plan = plan_resume(
        (old,), (cell,), ResumePolicy(3, frozenset({ExclusionCode.CELL_TIMEOUT})), store
    )
    assert plan.cells == (cell,)
    assert plan.attempts == (3,)
    assert store.load_cell_outcomes() == (old,)


def test_journals_reject_unknown_keys_and_negative_identity() -> None:
    from livebench_hermes_ab.artifacts import parse_cell_outcome_bytes
    from livebench_hermes_ab.domain import IntegrityError

    value = {
        "cell_journal_schema_version": 2,
        "cell": {"arm": "base", "pair_id": "p", "question_id": "q", "sample_index": -1},
        "elapsed_seconds": 1,
        "status": "valid",
        "answer_record": {"answer": "x"},
        "extra": True,
    }
    with pytest.raises(IntegrityError):
        parse_cell_outcome_bytes((json.dumps(value) + "\n").encode())


def test_prepare_stage_is_removed_when_home_configuration_fails(
    tmp_path: Path, monkeypatch
) -> None:
    from livebench_hermes_ab.config import load_config
    from livebench_hermes_ab.manifest import CompatibilityResult
    from livebench_hermes_ab.preparation import prepare_run

    config = load_config(Path("config.yaml"))
    source_home = tmp_path / "source-home"
    source_home.mkdir()
    (source_home / "auth.json").write_text("{}\n")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    run_dir = tmp_path / "run"
    with pytest.raises(Exception, match="OPENROUTER_API_KEY"):
        prepare_run(
            Path.cwd(),
            Path("config.yaml"),
            config,
            run_dir,
            CompatibilityResult("0.19.1", True, None),
            source_home=source_home,
        )
    assert not run_dir.exists()
    assert not tuple(tmp_path.glob(".run.*"))
