from livebench_hermes_ab.output_validation import mark_terminal_provider_call_failed


def test_only_terminal_provider_call_is_marked_failed() -> None:
    calls = [
        {"role": "reference", "status": "succeeded", "output_tokens": 7},
        {"role": "aggregator", "status": "succeeded", "output_tokens": 11},
    ]
    marked = mark_terminal_provider_call_failed(calls)
    assert marked[0] == calls[0]
    assert marked[1]["status"] == "failed_output"
    assert marked[1]["output_tokens"] == 11
    assert calls[1]["status"] == "succeeded"
