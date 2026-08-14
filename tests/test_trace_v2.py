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


def test_trace_validator_retains_sanitized_evidence_and_complete_call_ledger() -> None:
    expected = ExpectedTrace(
        CellId("moa", "p", "q", 0), "default", (("openrouter", "ref"),), ("openai", "agg")
    )
    record = {
        "preset": "default",
        "api_key": "must-not-survive",
        "references": [
            {
                "provider": "openrouter",
                "model": "ref",
                "output": "CANDIDATE: 42",
                "messages": [{"role": "user", "content": "Authorization: Bearer secret"}],
                "usage": {
                    "input_tokens": 2,
                    "output_tokens": 3,
                    "cache_read_tokens": 1,
                    "reasoning_tokens": 4,
                },
                "cost_usd": 0.125,
                "actual_cost_usd": 0.1,
                "cost_status": "actual",
                "cost_source": "provider_generation",
                "generation_id": "gen-ref",
            }
        ],
        "aggregator": {
            "provider": "openai",
            "model": "agg",
            "output": "42",
            "usage": {"input_tokens": 5, "output_tokens": 1},
            "cost_usd": 0.2,
            "cost_status": "estimated",
            "cost_source": "models_api",
            "generation_id": "gen-agg",
        },
    }

    value = validate_cell_trace((json.dumps(record) + "\n").encode(), expected, "42")

    assert value.exclusion is None
    assert value.sanitized_trace is not None
    encoded = json.dumps(value.sanitized_trace)
    assert "must-not-survive" not in encoded
    assert "Bearer secret" not in encoded
    assert encoded.count("[REDACTED]") >= 2
    assert [call.role for call in value.provider_calls] == ["reference", "aggregator"]
    reference, aggregator = value.provider_calls
    assert reference.input_tokens == 2
    assert reference.cache_read_tokens == 1
    assert reference.reasoning_tokens == 4
    assert reference.actual_cost_usd == 0.1
    assert reference.generation_id == "gen-ref"
    assert reference.usage_complete is True
    assert reference.cost_complete is True
    assert aggregator.input_tokens == 5
    assert aggregator.generation_id == "gen-agg"


def test_invalid_trace_preserves_sanitized_partial_evidence_and_missingness() -> None:
    expected = ExpectedTrace(
        CellId("moa", "p", "q", 0), "default", (("openrouter", "ref"),), ("openai", "agg")
    )
    record = {
        "preset": "wrong",
        "secret": "do-not-store",
        "references": [
            {
                "provider": "openrouter",
                "model": "ref",
                "output": "candidate",
                "usage": {"input_tokens": 2, "output_tokens": 3},
            }
        ],
        "aggregator": {"provider": "openai", "model": "agg", "output": "answer"},
    }

    value = validate_cell_trace((json.dumps(record) + "\n").encode(), expected, "answer")

    assert value.exclusion is not None
    assert value.sanitized_trace is not None
    assert "do-not-store" not in json.dumps(value.sanitized_trace)
    assert len(value.provider_calls) == 2
    assert value.provider_calls[0].status == "invalid_trace"
    assert value.provider_calls[1].usage_complete is False
