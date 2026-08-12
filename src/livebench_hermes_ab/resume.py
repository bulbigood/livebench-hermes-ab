from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .domain import CellId, CellOutcome, ExcludedOutcome, ExclusionCode


class AttemptStore(Protocol):
    def attempt_numbers(self, cell: CellId) -> tuple[int, ...]: ...


@dataclass(frozen=True, slots=True)
class ResumePolicy:
    max_attempts: int
    retryable_codes: frozenset[ExclusionCode]


@dataclass(frozen=True, slots=True)
class ResumePlan:
    cells: tuple[CellId, ...]
    attempts: tuple[int, ...]


def plan_resume(
    outcomes: tuple[CellOutcome, ...],
    planned: tuple[CellId, ...],
    policy: ResumePolicy,
    attempts_store: AttemptStore | None = None,
) -> ResumePlan:
    if len(set(planned)) != len(planned):
        raise ValueError("planned cells must be unique")
    if len({outcome.cell for outcome in outcomes}) != len(outcomes):
        raise ValueError("terminal outcomes must be unique")
    if not {outcome.cell for outcome in outcomes} <= set(planned):
        raise ValueError("terminal outcome outside planned matrix")
    existing = {outcome.cell: outcome for outcome in outcomes}
    selected: list[CellId] = []
    attempts: list[int] = []
    for cell in planned:
        outcome = existing.get(cell)
        persisted = attempts_store.attempt_numbers(cell) if attempts_store else ()
        next_attempt = max(persisted, default=0) + 1
        if outcome is None:
            selected.append(cell)
            attempts.append(next_attempt)
        elif (
            isinstance(outcome, ExcludedOutcome)
            and outcome.code in policy.retryable_codes
            and next_attempt <= policy.max_attempts
        ):
            selected.append(cell)
            attempts.append(next_attempt if attempts_store else 2)
    return ResumePlan(tuple(selected), tuple(attempts))
