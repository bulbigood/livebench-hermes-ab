from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from .agentic_trajectory import AgentAction, TrajectoryStatus


class ModelProtocolError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: float

    def __add__(self, other: ModelUsage) -> ModelUsage:
        return ModelUsage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            float(Decimal(str(self.cost_usd)) + Decimal(str(other.cost_usd))),
        )


@dataclass(frozen=True, slots=True)
class ModelBudget:
    max_turns: int
    max_input_tokens: int
    max_output_tokens: int
    max_cost_usd: float

    def __post_init__(self) -> None:
        if min(self.max_turns, self.max_input_tokens, self.max_output_tokens) < 1:
            raise ValueError("model token and turn budgets must be positive")
        if self.max_cost_usd < 0:
            raise ValueError("model cost budget cannot be negative")


@dataclass(frozen=True, slots=True)
class ModelTurn:
    response: str
    usage: ModelUsage


class ModelAdapter(Protocol):
    def next_turn(
        self, task_brief: str, observations: Sequence[dict[str, object]], budget: ModelBudget
    ) -> ModelTurn: ...


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@dataclass(frozen=True, slots=True)
class ModelLoopResult:
    status: TrajectoryStatus
    usage: ModelUsage
    private_turns_json: str

    def publish(self, private_path: Path, public_path: Path, context_digest: str) -> str:
        raw = self.private_turns_json.encode()
        _atomic_write(private_path, raw + b"\n")
        raw_digest = hashlib.sha256(raw).hexdigest()
        bound = hashlib.sha256(f"{context_digest}:{raw_digest}".encode()).hexdigest()
        public = {
            "schema_version": 1,
            "status": self.status.value,
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "cost_usd": self.usage.cost_usd,
            },
            "raw_model_turns_sha256": raw_digest,
            "context_digest": context_digest,
            "bound_model_loop_sha256": bound,
        }
        _atomic_write(
            public_path,
            (json.dumps(public, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        return bound


class FakeModelAdapter:
    def __init__(self, turns: Sequence[tuple[str, ModelUsage]]) -> None:
        self._turns = list(turns)
        self.calls = 0

    def next_turn(
        self, task_brief: str, observations: Sequence[dict[str, object]], budget: ModelBudget
    ) -> ModelTurn:
        del task_brief, observations, budget
        if self.calls >= len(self._turns):
            raise ModelProtocolError("fake adapter exhausted")
        response, usage = self._turns[self.calls]
        self.calls += 1
        return ModelTurn(response, usage)


def parse_model_action(payload: str) -> AgentAction:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ModelProtocolError("model action must be strict JSON") from error
    if not isinstance(raw, dict) or raw.get("kind") not in {"command", "submit"}:
        raise ModelProtocolError("unsupported model action kind")
    if raw["kind"] == "submit":
        if set(raw) != {"kind"}:
            raise ModelProtocolError("submit action contains unknown fields")
        return AgentAction.submit()
    if set(raw) != {"kind", "argv", "cwd"}:
        raise ModelProtocolError("command action contains unknown or missing fields")
    argv = raw["argv"]
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        raise ModelProtocolError("command argv must be a non-empty string array")
    if not isinstance(raw["cwd"], str):
        raise ModelProtocolError("command cwd must be a string")
    return AgentAction(tuple(argv), Path(raw["cwd"]))


def _over_budget(usage: ModelUsage, budget: ModelBudget) -> bool:
    return (
        usage.input_tokens > budget.max_input_tokens
        or usage.output_tokens > budget.max_output_tokens
        or usage.cost_usd > budget.max_cost_usd
    )


def run_model_loop(
    adapter: ModelAdapter,
    task_brief: str,
    budget: ModelBudget,
    execute: Callable[[AgentAction], dict[str, object]],
) -> ModelLoopResult:
    usage = ModelUsage(0, 0, 0.0)
    observations: list[dict[str, object]] = []
    turns: list[dict[str, object]] = []
    status = TrajectoryStatus.MISSING_SUBMISSION
    for _ in range(budget.max_turns):
        turn = adapter.next_turn(task_brief, observations, budget)
        usage = usage + turn.usage
        turns.append(
            {
                "response": turn.response,
                "usage": {
                    "input_tokens": turn.usage.input_tokens,
                    "output_tokens": turn.usage.output_tokens,
                    "cost_usd": turn.usage.cost_usd,
                },
            }
        )
        if _over_budget(usage, budget):
            status = TrajectoryStatus.LIMITS_EXCEEDED
            break
        try:
            action = parse_model_action(turn.response)
        except ModelProtocolError:
            status = TrajectoryStatus.INVALID_ACTION
            break
        if action.submission:
            status = TrajectoryStatus.SUBMITTED
            break
        observation = execute(action)
        observations.append(observation)
        turns[-1]["observation"] = observation
        if observation.get("kind") == "command_timeout":
            status = TrajectoryStatus.COMMAND_TIMEOUT
            break
        if observation.get("kind") == "invalid_action":
            status = TrajectoryStatus.INVALID_ACTION
            break
        if observation.get("returncode") != 0:
            status = TrajectoryStatus.COMMAND_FAILED
            break
    else:
        status = TrajectoryStatus.LIMITS_EXCEEDED
    return ModelLoopResult(
        status,
        usage,
        json.dumps(turns, sort_keys=True, separators=(",", ":")),
    )
