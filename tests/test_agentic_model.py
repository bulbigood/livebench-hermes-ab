from __future__ import annotations

import json
from pathlib import Path

import pytest

from livebench_hermes_ab.agentic_model import (
    FakeModelAdapter,
    ModelBudget,
    ModelProtocolError,
    ModelUsage,
    parse_model_action,
    run_model_loop,
)
from livebench_hermes_ab.agentic_trajectory import TrajectoryStatus


def test_parser_accepts_strict_structured_actions() -> None:
    command = parse_model_action('{"kind":"command","argv":["git","status","--short"],"cwd":"."}')
    assert command.argv == ("git", "status", "--short")
    assert not command.submission
    assert parse_model_action('{"kind":"submit"}').submission


@pytest.mark.parametrize(
    "payload",
    [
        "```bash\ngit status\n```",
        '{"kind":"command","argv":"git status","cwd":"."}',
        '{"kind":"command","argv":["git"],"cwd":".","extra":1}',
        '{"kind":"submit","argv":[]}',
        '{"kind":"unknown"}',
    ],
)
def test_parser_rejects_ambiguous_or_extra_fields(payload: str) -> None:
    with pytest.raises(ModelProtocolError):
        parse_model_action(payload)


def test_model_budget_rejects_excess_before_another_turn() -> None:
    adapter = FakeModelAdapter(
        [
            (
                '{"kind":"command","argv":["git","status","--short"],"cwd":"."}',
                ModelUsage(input_tokens=80, output_tokens=30, cost_usd=0.02),
            ),
            ('{"kind":"submit"}', ModelUsage(1, 1, 0.001)),
        ]
    )
    result = run_model_loop(
        adapter,
        "sanitized brief",
        ModelBudget(max_turns=3, max_input_tokens=100, max_output_tokens=25, max_cost_usd=0.05),
        lambda action: {"kind": "command", "returncode": 0, "stdout": "", "stderr": ""},
    )
    assert result.status is TrajectoryStatus.LIMITS_EXCEEDED
    assert adapter.calls == 1


def test_fake_adapter_drives_interactive_loop_without_provider(tmp_path: Path) -> None:
    adapter = FakeModelAdapter(
        [
            (
                '{"kind":"command","argv":["git","status","--short"],"cwd":"."}',
                ModelUsage(12, 8, 0.0),
            ),
            ('{"kind":"submit"}', ModelUsage(9, 3, 0.0)),
        ]
    )
    observations: list[dict[str, object]] = []

    def execute(action):
        value = {"kind": "command", "returncode": 0, "stdout": "", "stderr": ""}
        observations.append(value)
        return value

    result = run_model_loop(
        adapter,
        "sanitized brief",
        ModelBudget(3, 100, 100, 0.0),
        execute,
    )
    assert result.status is TrajectoryStatus.SUBMITTED
    assert result.usage == ModelUsage(21, 11, 0.0)
    assert len(observations) == 1
    assert json.loads(result.private_turns_json)[0]["response"].startswith("{")
