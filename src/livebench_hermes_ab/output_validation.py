from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

_TERMINAL_PROVIDER_FAILURE = re.compile(
    r"^\s*(?:❌\s*)?api(?:\s+call)?\s+failed\s+after\s+\d+\s+retries(?:\s*[:—-]|\s*$)",
    re.IGNORECASE,
)


def is_terminal_provider_failure(answer: str) -> bool:
    """Return whether Hermes surfaced an exhausted provider retry as the answer.

    Match only the beginning of the complete one-shot output. A normal answer
    that quotes or discusses the failure phrase must remain valid.
    """

    return _TERMINAL_PROVIDER_FAILURE.match(answer) is not None


def mark_terminal_provider_call_failed(
    raw_calls: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    calls = [dict(call) for call in raw_calls]
    if not calls:
        return calls
    terminal_index = next(
        (index for index in range(len(calls) - 1, -1, -1) if calls[index].get("role") == "aggregator"),
        next(
            (
                index
                for index in range(len(calls) - 1, -1, -1)
                if calls[index].get("role") == "acting"
            ),
            len(calls) - 1,
        ),
    )
    calls[terminal_index]["status"] = "failed_output"
    return calls
