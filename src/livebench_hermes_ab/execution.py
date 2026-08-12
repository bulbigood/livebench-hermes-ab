from __future__ import annotations

import base64
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from .artifacts import ArtifactStore, ExecutionBundle
from .domain import (
    AttemptDiagnostic,
    CellOutcome,
    CellSpec,
    ExcludedOutcome,
    ExclusionCode,
    HarnessExecutionError,
    ValidOutcome,
)
from .hermes import HermesRequest, HermesRunner
from .scheduler import ScheduledCell, Scheduler
from .trace_validation import ExpectedTrace, validate_cell_trace


class Workspace(Protocol):
    def cleanup(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CellRunResult:
    outcome: CellOutcome
    diagnostic: AttemptDiagnostic | None = None


def _trace_diagnostic(trace: bytes) -> AttemptDiagnostic:
    try:
        return AttemptDiagnostic("moa_trace", "utf-8", trace.decode("utf-8"))
    except UnicodeDecodeError:
        return AttemptDiagnostic("moa_trace", "base64", base64.b64encode(trace).decode("ascii"))


class CellRunner:
    def __init__(
        self,
        hermes: HermesRunner,
        workspace_factory: Callable[[CellSpec], Workspace | None],
        timeout_seconds: int = 1800,
    ):
        self.hermes, self.workspace_factory, self.timeout_seconds = (
            hermes,
            workspace_factory,
            timeout_seconds,
        )

    def run(self, cell: CellSpec) -> CellRunResult:
        workspace = None
        try:
            workspace = self.workspace_factory(cell)
            home = getattr(workspace, "home", None)
            if home is None:
                raise HarnessExecutionError("workspace factory did not provide an isolated home")
            answers: list[str] = []
            trace_audit: list[dict[str, int]] = []
            turns = cell.turns or (cell.prompt,)
            result = None
            for index, turn in enumerate(turns):
                if cell.turns:
                    parts = ([cell.system_prompt] if cell.system_prompt else []) + [turns[0]]
                    for previous_index in range(index):
                        parts.extend(
                            [
                                "Assistant's previous response:\n" + answers[previous_index],
                                turns[previous_index + 1],
                            ]
                        )
                    prompt = "\n\n".join(parts)
                else:
                    prompt = cell.prompt
                result = self.hermes.invoke(
                    HermesRequest(prompt, cell.hermes_profile, self.timeout_seconds, home)
                )
                outcome, usage = self._check_result(cell, workspace, result)
                if outcome is not None:
                    diagnostic = (
                        _trace_diagnostic(result.trace_bytes)
                        if outcome.code is ExclusionCode.INVALID_MOA_TRACE
                        and result.trace_bytes is not None
                        else None
                    )
                    return CellRunResult(outcome, diagnostic)
                if usage is not None:
                    trace_audit.append(usage)
                answers.append(result.stdout.strip())
            assert result is not None
            answer = answers[-1]
            record = {
                "question_id": cell.id.question_id,
                "sample_index": cell.id.sample_index,
                "answer": answer,
                "turns": answers,
                "trace_audit": trace_audit,
            }
            return CellRunResult(ValidOutcome(cell.id, record, result.elapsed_seconds))
        finally:
            if workspace is not None:
                workspace.cleanup()

    def _check_result(self, cell, workspace, result):
        if result.returncode == 124:
            return ExcludedOutcome(
                cell.id,
                ExclusionCode.CELL_TIMEOUT,
                result.stderr or "cell timeout",
                result.elapsed_seconds,
            ), None
        if result.returncode != 0:
            return ExcludedOutcome(
                cell.id,
                ExclusionCode.MODEL_OR_PROVIDER_FAILURE,
                result.stderr or f"Hermes exited {result.returncode}",
                result.elapsed_seconds,
            ), None
        answer = result.stdout.strip()
        if not answer or answer.casefold() == "(empty response)":
            return ExcludedOutcome(
                cell.id,
                ExclusionCode.INVALID_MODEL_OUTPUT,
                "empty model output",
                result.elapsed_seconds,
            ), None
        expected = getattr(workspace, "expected_trace", None)
        if expected is not None:
            if result.trace_bytes is None or not isinstance(expected, ExpectedTrace):
                return ExcludedOutcome(
                    cell.id,
                    ExclusionCode.INVALID_MOA_TRACE,
                    "missing MoA trace",
                    result.elapsed_seconds,
                ), None
            validation = validate_cell_trace(result.trace_bytes, expected, answer)
            if validation.exclusion is not None:
                return ExcludedOutcome(
                    cell.id,
                    validation.exclusion.code,
                    validation.exclusion.reason,
                    result.elapsed_seconds,
                ), None
            assert validation.usage is not None
            usage = validation.usage
            return None, {
                "reference_calls": usage.reference_calls,
                "reference_input_tokens": usage.reference_input_tokens,
                "reference_output_tokens": usage.reference_output_tokens,
                "trace": result.trace_bytes.decode("utf-8"),
                "answer": answer,
                "expected": {
                    "preset": expected.preset,
                    "references": [list(identity) for identity in expected.references],
                    "aggregator": list(expected.aggregator),
                },
            }
        return None, None


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    complete: bool
    outcomes: tuple[CellOutcome, ...]
    fatal: HarnessExecutionError | None


class ExecutionService:
    def __init__(self, scheduler: Scheduler, runner: CellRunner, store: ArtifactStore):
        self.scheduler, self.runner, self.store = scheduler, runner, store

    def execute(
        self, cells: Sequence[CellSpec], attempts: Sequence[int] | None = None
    ) -> ExecutionResult:
        terminal: list[CellOutcome] = []
        attempt_by_cell = {
            cell.id: attempts[index] if attempts else 1 for index, cell in enumerate(cells)
        }

        def persist(result: CellRunResult) -> None:
            outcome = result.outcome
            self.store.write_cell_attempt(attempt_by_cell[outcome.cell], outcome, result.diagnostic)
            self.store.promote_cell_outcome(outcome)
            terminal.append(outcome)

        result = self.scheduler.execute(
            tuple(ScheduledCell(i, cell) for i, cell in enumerate(cells)), self.runner.run, persist
        )
        if result.fatal is not None:
            return ExecutionResult(False, tuple(terminal), result.fatal)
        all_outcomes = self.store.load_cell_outcomes()
        self.store.publish_execution(ExecutionBundle(all_outcomes))
        return ExecutionResult(True, all_outcomes, None)
