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
        self.expected_provider_identities: tuple[tuple[str, str, str], ...] = ()

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


def test_zero_exit_provider_failure_text_is_excluded(tmp_path: Path) -> None:
    cell = CellSpec(CellId("base", "p", "q", 1), "prompt", "base", 1)

    class FailedProviderRunner:
        def invoke(self, request: HermesRequest) -> HermesResult:
            return HermesResult(
                0,
                "API call failed after 3 retries: [Errno 32] Broken pipe",
                "",
                1.0,
                None,
            )

    result = CellRunner(
        FailedProviderRunner(), lambda _cell: FakeWorkspace(tmp_path / "workspace")
    ).run(cell)

    assert isinstance(result.outcome, ExcludedOutcome)
    assert result.outcome.code is ExclusionCode.MODEL_OR_PROVIDER_FAILURE
    assert result.outcome.reason == "Hermes returned a terminal provider failure"


def test_multiturn_terminal_failure_preserves_prior_provider_calls(tmp_path: Path) -> None:
    cell = CellSpec(
        CellId("moa", "p", "q", 1),
        "prompt",
        "moa",
        4,
        turns=("first", "second"),
    )

    class SequenceRunner:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, request: HermesRequest) -> HermesResult:
            self.calls += 1
            if self.calls == 1:
                return HermesResult(0, "first answer", "", 1.0, None)
            return HermesResult(
                0,
                "API call failed after 3 retries: [Errno 32] Broken pipe",
                "",
                1.0,
                None,
            )

    workspace = FakeWorkspace(tmp_path / "workspace")
    workspace.expected_provider_identities = (
        ("reference", "openrouter", "ref"),
        ("aggregator", "openai-codex", "acting"),
    )
    result = CellRunner(SequenceRunner(), lambda _cell: workspace).run(cell)

    assert isinstance(result.outcome, ExcludedOutcome)
    assert result.outcome.evidence is not None
    calls = result.outcome.evidence["provider_calls"]
    assert isinstance(calls, list)
    assert [(call["role"], call["status"]) for call in calls] == [
        ("reference", "succeeded"),
        ("aggregator", "succeeded"),
        ("reference", "unknown"),
        ("aggregator", "failed_output"),
    ]


def test_provider_failure_phrase_inside_normal_answer_is_not_excluded(tmp_path: Path) -> None:
    cell = CellSpec(CellId("base", "p", "q", 1), "prompt", "base", 1)

    class QuotingRunner:
        def invoke(self, request: HermesRequest) -> HermesResult:
            return HermesResult(
                0,
                'The phrase "API call failed after 3 retries" is an error message.',
                "",
                1.0,
                None,
            )

    result = CellRunner(
        QuotingRunner(), lambda _cell: FakeWorkspace(tmp_path / "workspace")
    ).run(cell)
    assert isinstance(result.outcome, ValidOutcome)


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
    assert result.outcomes[0].evidence is not None
    assert result.outcomes[0].evidence["provider_calls"][0]["status"] == "invalid_trace"
    assert result.outcomes[0].evidence["moa_trace"]["references"][0]["error"] == (
        "upstream returned no content"
    )
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


def test_valid_trace_is_sanitized_and_embedded_with_provider_ledger(tmp_path: Path) -> None:
    cell = CellSpec(CellId("moa", "p", "q", 1), "prompt", "moa", 2)
    trace = json.dumps(
        {
            "preset": "default",
            "api_key": "private",
            "references": [
                {
                    "provider": "openrouter",
                    "model": "ref",
                    "output": "CANDIDATE: answer",
                    "usage": {"input_tokens": 3, "output_tokens": 2},
                    "cost_usd": 0.01,
                    "cost_status": "estimated",
                }
            ],
            "aggregator": {
                "provider": "openai",
                "model": "agg",
                "output": "answer",
                "usage": {"input_tokens": 5, "output_tokens": 1},
            },
        }
    ).encode()

    class TraceRunner:
        def invoke(self, request: HermesRequest) -> HermesResult:
            return HermesResult(0, "answer", "", 0.5, trace + b"\n")

    class TraceWorkspace(FakeWorkspace):
        expected_trace = ExpectedTrace(
            cell.id, "default", (("openrouter", "ref"),), ("openai", "agg")
        )

    result = CellRunner(
        TraceRunner(), lambda _cell: TraceWorkspace(tmp_path / "workspace")
    ).run(cell)

    assert isinstance(result.outcome, ValidOutcome)
    encoded = json.dumps(dict(result.outcome.answer_record))
    assert "private" not in encoded
    assert result.outcome.answer_record["moa_trace"]["api_key"] == "[REDACTED]"
    assert len(result.outcome.answer_record["provider_calls"]) == 2
    assert result.outcome.answer_record["provider_calls"][1]["role"] == "aggregator"


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


def test_invalid_trace_diagnostic_redacts_secret_fields(tmp_path: Path) -> None:
    cell = CellSpec(CellId("moa", "p", "q", 1), "prompt", "moa", 2)
    trace = (
        json.dumps(
            {
                "api_key": "top-secret",
                "nested": {"Authorization": "Bearer private", "safe": "kept"},
            }
        ).encode()
        + b"\n"
    )

    class TraceRunner:
        def invoke(self, request: HermesRequest) -> HermesResult:
            return HermesResult(0, "answer", "", 0.5, trace)

    class TraceWorkspace(FakeWorkspace):
        expected_trace = ExpectedTrace(
            cell.id, "default", (("openrouter", "ref"),), ("openai", "agg")
        )

    store = FilesystemArtifactStore(tmp_path / "run")
    ExecutionService(
        Scheduler(1),
        CellRunner(TraceRunner(), lambda _cell: TraceWorkspace(tmp_path / "workspace")),
        store,
    ).execute((cell,))

    attempt = json.loads(next((tmp_path / "run" / "attempts").glob("*.json")).read_text())
    diagnostic = json.loads(attempt["diagnostic"]["content"])
    assert diagnostic == {
        "api_key": "[REDACTED]",
        "nested": {"Authorization": "[REDACTED]", "safe": "kept"},
    }
    assert "top-secret" not in attempt["diagnostic"]["content"]
    assert "Bearer private" not in attempt["diagnostic"]["content"]
