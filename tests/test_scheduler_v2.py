import threading
import time

import pytest

from livebench_hermes_ab.domain import (
    CellId,
    CellSpec,
    ExcludedOutcome,
    ExclusionCode,
    HarnessExecutionError,
)
from livebench_hermes_ab.scheduler import ScheduledCell, Scheduler


def _cell(index: int) -> CellSpec:
    return CellSpec(CellId("base", f"p{index}", f"q{index}", 0), "prompt", "base", 1)


def test_exclusions_continue_but_harness_failure_stops_admission_and_drains() -> None:
    entered = threading.Barrier(2)
    finished: list[int] = []
    cells = tuple(ScheduledCell(i, _cell(i)) for i in range(5))

    def run(cell: CellSpec):
        index = int(cell.id.pair_id[1:])
        if index < 2:
            entered.wait()
        if index == 0:
            raise HarnessExecutionError("fatal-zero")
        if index == 1:
            time.sleep(0.02)
        finished.append(index)
        return ExcludedOutcome(cell.id, ExclusionCode.CELL_TIMEOUT, "local", 1.0)

    terminal = []
    result = Scheduler(workers=2).execute(cells, run, terminal.append)
    assert isinstance(result.fatal, HarnessExecutionError)
    assert str(result.fatal) == "fatal-zero"
    assert finished == [1]
    assert len(terminal) == 1


def test_fatal_selection_uses_lowest_submission_index() -> None:
    barrier = threading.Barrier(2)
    cells = tuple(ScheduledCell(i, _cell(i)) for i in range(2))

    def run(cell: CellSpec):
        barrier.wait()
        raise HarnessExecutionError(cell.id.pair_id)

    result = Scheduler(workers=2).execute(cells, run, lambda _: None)
    assert str(result.fatal) == "p0"


def test_balanced_workers_run_multiple_complete_arm_waves() -> None:
    entered = threading.Barrier(9)
    release = threading.Event()
    seen: list[str] = []
    cells = tuple(
        ScheduledCell(index, CellSpec(CellId(arm, pair, f"q-{pair}", 1), "prompt", arm, 1))
        for index, (pair, arm) in enumerate(
            (pair, arm)
            for pair in ("p0", "p1", "p2")
            for arm in ("base", "medium", "moa-a", "moa-b")
        )
    )

    def run(cell: CellSpec):
        seen.append(cell.id.pair_id)
        if cell.id.pair_id in {"p0", "p1"}:
            entered.wait()
            release.wait()
        return ExcludedOutcome(cell.id, ExclusionCode.CELL_TIMEOUT, "local", 1.0)

    result: list[object] = []
    thread = threading.Thread(
        target=lambda: result.append(
            Scheduler(workers=8, mode="balanced_waves").execute(cells, run, lambda _: None)
        )
    )
    thread.start()
    entered.wait(timeout=2)
    assert seen.count("p0") == 4
    assert seen.count("p1") == 4
    assert "p2" not in seen
    release.set()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert seen.count("p2") == 4


def test_balanced_scheduler_rejects_incomplete_or_incompatible_waves() -> None:
    complete = tuple(
        ScheduledCell(index, CellSpec(CellId(arm, "p0", "q", 1), "prompt", arm, 1))
        for index, arm in enumerate(("base", "medium", "moa-a", "moa-b"))
    )
    with pytest.raises(ValueError, match="multiple of arm wave size"):
        Scheduler(workers=7, mode="balanced_waves").execute(
            complete,
            lambda cell: ExcludedOutcome(cell.id, ExclusionCode.CELL_TIMEOUT, "local", 1.0),
            lambda _: None,
        )

    incomplete = complete + (
        ScheduledCell(4, CellSpec(CellId("base", "p1", "q", 1), "prompt", "base", 1)),
    )
    with pytest.raises(ValueError, match="complete, equal-sized"):
        Scheduler(workers=8, mode="balanced_waves").execute(
            incomplete,
            lambda cell: ExcludedOutcome(cell.id, ExclusionCode.CELL_TIMEOUT, "local", 1.0),
            lambda _: None,
        )
