from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from .config import ArmConfig, SelectionConfig
from .domain import CellId, CellSpec, ConfigError


@dataclass(frozen=True, slots=True)
class Question:
    question_id: str
    category: str
    family: str
    turns: tuple[str, ...]
    raw: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class WorkloadPlan:
    arm_order: tuple[str, ...]
    questions: tuple[Question, ...]
    cells: tuple[CellSpec, ...]
    waves: tuple[tuple[CellSpec, ...], ...]
    expected_provider_calls: int


def select_questions(
    catalog: Sequence[Question], config: SelectionConfig, release: str
) -> tuple[Question, ...]:
    by_id = {question.question_id: question for question in catalog}
    selected = []
    for category, specs in config.scenarios.items():
        for spec in specs:
            question = by_id.get(spec["id"])
            if question is None:
                raise ConfigError(f"selected scenario unavailable: {spec['id']}")
            if question.category != category or question.family != spec["family"]:
                raise ConfigError(f"selected scenario metadata mismatch: {spec['id']}")
            released = str(question.raw.get("livebench_release_date", ""))
            removed = str(question.raw.get("livebench_removal_date", ""))
            if not released or released > release or (removed and removed <= release):
                raise ConfigError(
                    f"selected scenario not active for release {release}: {spec['id']}"
                )
            selected.append(question)
    if len({q.question_id for q in selected}) != len(selected):
        raise ConfigError("selection contains duplicate scenario IDs")
    return tuple(selected)


def _prompt(question: Question) -> str:
    if not question.turns or not all(turn.strip() for turn in question.turns):
        raise ConfigError(f"question {question.question_id} has invalid turns")
    system = question.raw.get("system_prompt")
    return "\n\n".join(([str(system)] if system else []) + [question.turns[0]])


def build_workload(
    questions: Sequence[Question],
    arms: Sequence[ArmConfig],
    samples: int,
    seed: int = 0,
) -> WorkloadPlan:
    if samples < 1 or not arms:
        raise ConfigError("workload requires arms and positive samples")
    pairs = [
        (question, sample)
        for question in sorted(questions, key=lambda q: q.question_id)
        for sample in range(1, samples + 1)
    ]
    random.Random(seed).shuffle(pairs)
    cells: list[CellSpec] = []
    waves: list[tuple[CellSpec, ...]] = []
    calls = 0
    for pair_index, (question, sample_index) in enumerate(pairs):
        pair_id = hashlib.sha256(
            f"{seed}:{question.question_id}:{sample_index}".encode()
        ).hexdigest()[:16]
        rotated = tuple(arms[pair_index % len(arms) :]) + tuple(arms[: pair_index % len(arms)])
        wave = []
        for arm in rotated:
            cell = CellSpec(
                CellId(arm.name, pair_id, question.question_id, sample_index),
                _prompt(question),
                arm.name,
                arm.expected_provider_calls * len(question.turns),
                question.turns,
                str(question.raw["system_prompt"]) if question.raw.get("system_prompt") else None,
            )
            cells.append(cell)
            wave.append(cell)
            calls += arm.expected_provider_calls * len(question.turns)
        waves.append(tuple(wave))
    return WorkloadPlan(
        tuple(arm.name for arm in arms), tuple(questions), tuple(cells), tuple(waves), calls
    )


def question_from_record(value: Mapping[str, object]) -> Question:
    turns = value.get("turns")
    if not isinstance(turns, list):
        raise ConfigError("question turns must be a list")
    return Question(
        str(value.get("question_id", "")),
        str(value.get("category", "")),
        str(value.get("task", "")),
        tuple(str(v) for v in turns),
        MappingProxyType(dict(value)),
    )
