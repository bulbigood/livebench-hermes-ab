import json
from pathlib import Path

from livebench_hermes_ab.artifacts import FilesystemArtifactStore
from livebench_hermes_ab.domain import (
    CellId,
    CellSpec,
    ExcludedOutcome,
    ExclusionCode,
    HarnessExecutionError,
    ValidOutcome,
)
from livebench_hermes_ab.execution import CellRunner, ExecutionService
from livebench_hermes_ab.hermes import HermesRequest, HermesResult
from livebench_hermes_ab.scheduler import Scheduler
from livebench_hermes_ab.trace_validation import ExpectedTrace


class FakeRunner:
    def invoke(self, request: HermesRequest) -> HermesResult:
        if request.prompt == "fatal":
            raise HarnessExecutionError("workspace failed")
        return HermesResult(0, "answer", "", 0.5, None)


class FakeWorkspace:
    def __init__(self, home: Path):
        self.home = home

    def cleanup(self) -> None:
        pass


def test_cell_runner_and_execution_service_publish_only_on_complete(tmp_path: Path) -> None:
    good = CellSpec(CellId("base", "p1", "q1", 1), "ok", "base", 1)
    runner = CellRunner(FakeRunner(), lambda _cell: FakeWorkspace(tmp_path))
    assert isinstance(runner.run(good).outcome, ValidOutcome)
    store = FilesystemArtifactStore(tmp_path / "complete")
    result = ExecutionService(Scheduler(1), runner, store).execute((good,))
    assert result.complete and store.current_generation("execution") is not None

    fatal = CellSpec(CellId("base", "p2", "q2", 1), "fatal", "base", 1)
    store2 = FilesystemArtifactStore(tmp_path / "fatal")
    result2 = ExecutionService(Scheduler(1), runner, store2).execute((fatal,))
    assert not result2.complete and store2.current_generation("execution") is None


def test_invalid_moa_trace_is_preserved_in_immutable_attempt_before_cleanup(
    tmp_path: Path,
) -> None:
    cell = CellSpec(CellId("moa", "p", "q", 1), "prompt", "moa", 2)
    trace = json.dumps(
        {
            "preset": "default",
            "references": [
                {
                    "provider": "openrouter",
                    "model": "ref",
                    "output": "",
                    "error": "upstream returned no content",
                    "usage": {"input_tokens": 3, "output_tokens": 0},
                }
            ],
            "aggregator": {"provider": "openai", "model": "agg", "output": "answer"},
        }
    ).encode()

    class TraceRunner:
        def invoke(self, request: HermesRequest) -> HermesResult:
            return HermesResult(0, "answer", "", 0.5, trace + b"\n")

    class TraceWorkspace(FakeWorkspace):
        expected_trace = ExpectedTrace(
            cell.id, "default", (("openrouter", "ref"),), ("openai", "agg")
        )

        def cleanup(self) -> None:
            self.home.mkdir(exist_ok=True)
            (self.home / "cleaned").write_text("yes")

    store = FilesystemArtifactStore(tmp_path / "run")
    runner = CellRunner(TraceRunner(), lambda _cell: TraceWorkspace(tmp_path / "workspace"))
    result = ExecutionService(Scheduler(1), runner, store).execute((cell,))

    assert isinstance(result.outcomes[0], ExcludedOutcome)
    assert result.outcomes[0].code is ExclusionCode.INVALID_MOA_TRACE
    attempt = json.loads(next((tmp_path / "run" / "attempts").glob("*.json")).read_text())
    assert attempt["attempt_schema_version"] == 1
    assert attempt["outcome"]["reason"] == "empty or degraded reference"
    assert attempt["diagnostic"] == {
        "kind": "moa_trace",
        "encoding": "utf-8",
        "content": (trace + b"\n").decode(),
    }
    promoted = json.loads(next((tmp_path / "run" / "cells").glob("*.json")).read_text())
    assert "diagnostic" not in promoted
    generation = store.current_generation("execution")
    assert generation is not None
    assert b'"diagnostic"' not in (generation / "outcomes.jsonl").read_bytes()
    assert (tmp_path / "workspace" / "cleaned").read_text() == "yes"


def test_non_utf8_moa_trace_is_excluded_and_preserved_as_base64(tmp_path: Path) -> None:
    cell = CellSpec(CellId("moa", "p", "q", 1), "prompt", "moa", 2)

    class BinaryTraceRunner:
        def invoke(self, request: HermesRequest) -> HermesResult:
            return HermesResult(0, "answer", "", 0.5, b"\xff\xfe")

    class TraceWorkspace(FakeWorkspace):
        expected_trace = ExpectedTrace(
            cell.id, "default", (("openrouter", "ref"),), ("openai", "agg")
        )

    store = FilesystemArtifactStore(tmp_path / "run")
    result = ExecutionService(
        Scheduler(1),
        CellRunner(BinaryTraceRunner(), lambda _cell: TraceWorkspace(tmp_path / "workspace")),
        store,
    ).execute((cell,))

    assert isinstance(result.outcomes[0], ExcludedOutcome)
    attempt = json.loads(next((tmp_path / "run" / "attempts").glob("*.json")).read_text())
    assert attempt["diagnostic"] == {
        "kind": "moa_trace",
        "encoding": "base64",
        "content": "//4=",
    }
