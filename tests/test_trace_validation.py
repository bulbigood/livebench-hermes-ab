import json
from pathlib import Path

import pytest

from livebench_hermes_ab.core import ContractError
from livebench_hermes_ab.trace_validation import validate_moa_traces


def make_run(
    tmp_path: Path,
    reference_output_tokens: int = 2,
    reference_output: str = "advice",
) -> Path:
    run = tmp_path / "run"
    (run / "raw").mkdir(parents=True)
    trace_dir = run / "homes/moa/moa-traces"
    trace_dir.mkdir(parents=True)
    answer = {
        "question_id": "q1",
        "choices": [{"index": 0, "turns": ["answer"]}],
    }
    (run / "raw/hermes-moa.jsonl").write_text(json.dumps(answer) + "\n")
    trace = {
        "preset": "default",
        "references": [
            {
                "provider": "openrouter",
                "model": "minimax/minimax-m3",
                "output": reference_output,
                "usage": {"input_tokens": 3, "output_tokens": reference_output_tokens},
            }
        ],
        "aggregator": {
            "provider": "openai-codex",
            "model": "gpt-5.6-sol",
            "output": "answer",
        },
    }
    (trace_dir / "s.jsonl").write_text(json.dumps(trace) + "\n")
    return run


def test_trace_validator_accepts_complete_reference_and_matching_answer(tmp_path: Path):
    audit = validate_moa_traces(make_run(tmp_path), expected_count=1)
    assert audit["status"] == "valid"
    assert audit["reference_calls"] == 1
    assert audit["answer_trace_hashes_match"] is True


def test_trace_validator_rejects_missing_reference_usage(tmp_path: Path):
    with pytest.raises(ContractError, match="missing reference output usage"):
        validate_moa_traces(make_run(tmp_path, reference_output_tokens=0), expected_count=1)


def test_trace_validator_rejects_hermes_empty_response_sentinel(tmp_path: Path):
    run = make_run(tmp_path, reference_output="(empty response)", reference_output_tokens=10_000)
    with pytest.raises(ContractError, match="degraded reference output"):
        validate_moa_traces(run, expected_count=1)
