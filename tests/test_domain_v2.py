from dataclasses import FrozenInstanceError

import pytest

from livebench_hermes_ab.domain import CellId, ExcludedOutcome, ExclusionCode, ValidOutcome


def test_cell_outcomes_are_typed_and_immutable() -> None:
    cell = CellId("base", "pair-1", "q-1", 0)
    valid = ValidOutcome(cell, {"answer": "ok"}, 1.25)
    excluded = ExcludedOutcome(cell, ExclusionCode.CELL_TIMEOUT, "timed out", None)

    assert valid.cell == excluded.cell
    assert excluded.code.value == "CELL_TIMEOUT"
    with pytest.raises(FrozenInstanceError):
        cell.arm = "changed"  # type: ignore[misc]
