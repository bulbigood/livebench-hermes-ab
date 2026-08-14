from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Literal, TypeAlias


class HarnessError(Exception):
    """Base class for expected harness failures."""


class ConfigError(HarnessError, ValueError):
    pass


class ManifestError(HarnessError, ValueError):
    pass


class UnsupportedSchemaVersion(ManifestError):
    pass


class IntegrityError(HarnessError):
    pass


class PersistenceError(HarnessError):
    pass


class HarnessExecutionError(HarnessError):
    pass


class ExclusionCode(str, Enum):
    CELL_TIMEOUT = "CELL_TIMEOUT"
    MODEL_OR_PROVIDER_FAILURE = "MODEL_OR_PROVIDER_FAILURE"
    INVALID_MOA_TRACE = "INVALID_MOA_TRACE"
    INVALID_MODEL_OUTPUT = "INVALID_MODEL_OUTPUT"


@dataclass(frozen=True, slots=True, order=True)
class CellId:
    arm: str
    pair_id: str
    question_id: str
    sample_index: int


@dataclass(frozen=True, slots=True)
class CellSpec:
    id: CellId
    prompt: str
    hermes_profile: str
    expected_provider_calls: int
    turns: tuple[str, ...] = ()
    system_prompt: str | None = None


@dataclass(frozen=True, slots=True)
class ValidOutcome:
    cell: CellId
    answer_record: Mapping[str, object]
    elapsed_seconds: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "answer_record", MappingProxyType(dict(self.answer_record)))


@dataclass(frozen=True, slots=True)
class ExcludedOutcome:
    cell: CellId
    code: ExclusionCode
    reason: str
    elapsed_seconds: float | None
    evidence: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.evidence is not None:
            object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))


CellOutcome: TypeAlias = ValidOutcome | ExcludedOutcome


@dataclass(frozen=True, slots=True)
class AttemptDiagnostic:
    kind: Literal["moa_trace"]
    encoding: Literal["utf-8", "base64"]
    content: str


@dataclass(frozen=True, slots=True)
class AttemptId:
    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError("attempt ID must be positive")


@dataclass(frozen=True, slots=True)
class CellAttempt:
    attempt_id: AttemptId
    outcome: CellOutcome
