import json

from livebench_hermes_ab.domain import CellId, ExclusionCode
from livebench_hermes_ab.trace_validation import ExpectedTrace, validate_cell_trace


def test_one_trace_validator_owns_usage_and_answer_matching() -> None:
    expected = ExpectedTrace(
        CellId("moa", "p", "q", 0), "default", (("openrouter", "ref"),), ("openai", "agg")
    )
    record = {
        "preset": "default",
        "references": [
            {
                "provider": "openrouter",
                "model": "ref",
                "output": "r",
                "usage": {"input_tokens": 2, "output_tokens": 3},
            }
        ],
        "aggregator": {"provider": "openai", "model": "agg", "output": "answer"},
    }
    valid = validate_cell_trace((json.dumps(record) + "\n").encode(), expected, " answer ")
    assert valid.usage and valid.usage.reference_output_tokens == 3
    bad = validate_cell_trace(b"not json", expected, "answer")
    assert bad.exclusion and bad.exclusion.code is ExclusionCode.INVALID_MOA_TRACE
