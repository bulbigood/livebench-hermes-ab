from pathlib import Path

from livebench_hermes_ab.artifacts import FilesystemArtifactStore
from livebench_hermes_ab.domain import (
    CellId,
    CellSpec,
    HarnessExecutionError,
    ValidOutcome,
)
from livebench_hermes_ab.execution import CellRunner, ExecutionService
from livebench_hermes_ab.hermes import HermesRequest, HermesResult
from livebench_hermes_ab.scheduler import Scheduler


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
    assert isinstance(runner.run(good), ValidOutcome)
    store = FilesystemArtifactStore(tmp_path / "complete")
    result = ExecutionService(Scheduler(1), runner, store).execute((good,))
    assert result.complete and store.current_generation("execution") is not None

    fatal = CellSpec(CellId("base", "p2", "q2", 1), "fatal", "base", 1)
    store2 = FilesystemArtifactStore(tmp_path / "fatal")
    result2 = ExecutionService(Scheduler(1), runner, store2).execute((fatal,))
    assert not result2.complete and store2.current_generation("execution") is None
