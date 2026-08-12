from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass

from .domain import CellOutcome, CellSpec, HarnessExecutionError


@dataclass(frozen=True, slots=True)
class ScheduledCell:
    submission_index: int
    cell: CellSpec


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    submitted: int
    terminal: int
    fatal: HarnessExecutionError | None


class Scheduler:
    def __init__(self, workers: int, mode: str = "streaming"):
        if workers < 1:
            raise ValueError("workers must be positive")
        if mode not in {"streaming", "balanced_waves"}:
            raise ValueError("invalid scheduling mode")
        self.workers, self.mode = workers, mode

    def execute(
        self,
        cells: Sequence[ScheduledCell],
        run_cell: Callable[[CellSpec], CellOutcome],
        on_terminal: Callable[[CellOutcome], None],
    ) -> ScheduleResult:
        if self.mode == "balanced_waves":
            return self._execute_waves(cells, run_cell, on_terminal)
        pending_index = submitted = terminal = 0
        fatal: list[tuple[int, HarnessExecutionError]] = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            active: dict[Future[CellOutcome], ScheduledCell] = {}
            while pending_index < len(cells) and len(active) < self.workers:
                scheduled = cells[pending_index]
                pending_index += 1
                active[executor.submit(run_cell, scheduled.cell)] = scheduled
                submitted += 1
            while active:
                done, _ = wait(active, return_when=FIRST_COMPLETED)
                ordered_done = sorted(done, key=lambda future: active[future].submission_index)
                for future in ordered_done:
                    scheduled = active.pop(future)
                    try:
                        outcome = future.result()
                    except HarnessExecutionError as exc:
                        fatal.append((scheduled.submission_index, exc))
                    except Exception as exc:  # noqa: BLE001 -- worker defects are harness-fatal
                        fatal.append((scheduled.submission_index, HarnessExecutionError(str(exc))))
                    else:
                        on_terminal(outcome)
                        terminal += 1
                if fatal:
                    for future in active:
                        future.cancel()
                else:
                    while pending_index < len(cells) and len(active) < self.workers:
                        scheduled = cells[pending_index]
                        pending_index += 1
                        active[executor.submit(run_cell, scheduled.cell)] = scheduled
                        submitted += 1
        return ScheduleResult(
            submitted, terminal, min(fatal, key=lambda item: item[0])[1] if fatal else None
        )

    def _execute_waves(
        self,
        cells: Sequence[ScheduledCell],
        run_cell: Callable[[CellSpec], CellOutcome],
        on_terminal: Callable[[CellOutcome], None],
    ) -> ScheduleResult:
        submitted = terminal = 0
        fatal: list[tuple[int, HarnessExecutionError]] = []
        groups: list[list[ScheduledCell]] = []
        for cell in cells:
            if not groups or groups[-1][0].cell.id.pair_id != cell.cell.id.pair_id:
                groups.append([])
            groups[-1].append(cell)
        if groups:
            wave_size = len(groups[0])
            if any(len(group) != wave_size for group in groups):
                raise ValueError("balanced scheduling requires complete, equal-sized arm waves")
            if self.workers % wave_size:
                raise ValueError("balanced workers must be a multiple of arm wave size")
        batches: list[list[ScheduledCell]] = []
        for group in groups:
            if len(group) > self.workers:
                raise ValueError("balanced wave exceeds worker count")
            if not batches or len(batches[-1]) + len(group) > self.workers:
                batches.append([])
            batches[-1].extend(group)
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for batch in batches:
                barrier = threading.Barrier(len(batch))

                def start_together(
                    item: ScheduledCell, start_barrier: threading.Barrier = barrier
                ) -> CellOutcome:
                    start_barrier.wait()
                    return run_cell(item.cell)

                futures = {executor.submit(start_together, item): item for item in batch}
                submitted += len(batch)
                for future, item in futures.items():
                    try:
                        outcome = future.result()
                    except HarnessExecutionError as exc:
                        fatal.append((item.submission_index, exc))
                    except Exception as exc:  # noqa: BLE001 -- worker defects are harness-fatal
                        fatal.append((item.submission_index, HarnessExecutionError(str(exc))))
                    else:
                        on_terminal(outcome)
                        terminal += 1
                if fatal:
                    break
        return ScheduleResult(
            submitted, terminal, min(fatal, key=lambda item: item[0])[1] if fatal else None
        )
