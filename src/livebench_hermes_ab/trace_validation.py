from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .domain import CellId, ExcludedOutcome, ExclusionCode


@dataclass(frozen=True, slots=True)
class ExpectedTrace:
    cell: CellId
    preset: str
    references: tuple[tuple[str, str], ...]
    aggregator: tuple[str, str]


@dataclass(frozen=True, slots=True)
class TraceUsage:
    reference_input_tokens: int
    reference_output_tokens: int
    reference_calls: int


@dataclass(frozen=True, slots=True)
class TraceValidation:
    usage: TraceUsage | None
    exclusion: ExcludedOutcome | None


def _hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode()).hexdigest()


def validate_cell_trace(
    trace_bytes: bytes, expected: ExpectedTrace, answer: str
) -> TraceValidation:
    try:
        lines = [json.loads(line) for line in trace_bytes.splitlines() if line.strip()]
        if len(lines) != 1:
            raise ValueError("expected exactly one trace record")
        record = lines[0]
        if record.get("preset") != expected.preset:
            raise ValueError("unexpected preset")
        references = record.get("references")
        if not isinstance(references, list) or len(references) != len(expected.references):
            raise ValueError("unexpected reference count")
        input_tokens = output_tokens = 0
        for reference, (provider, model) in zip(references, expected.references, strict=True):
            if reference.get("provider") != provider or reference.get("model") != model:
                raise ValueError("unexpected reference identity")
            output = str(reference.get("output") or "").strip()
            if not output or output.casefold() == "(empty response)":
                raise ValueError("empty or degraded reference")
            usage = reference.get("usage") or {}
            out = int(usage.get("output_tokens") or 0)
            if out <= 0:
                raise ValueError("missing reference output usage")
            input_tokens += int(usage.get("input_tokens") or 0)
            output_tokens += out
        aggregator = record.get("aggregator") or {}
        if (aggregator.get("provider"), aggregator.get("model")) != expected.aggregator:
            raise ValueError("unexpected aggregator identity")
        output = str(aggregator.get("output") or "")
        if not output.strip() or _hash(output) != _hash(answer):
            raise ValueError("aggregator output does not match answer")
        return TraceValidation(TraceUsage(input_tokens, output_tokens, len(references)), None)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return TraceValidation(
            None, ExcludedOutcome(expected.cell, ExclusionCode.INVALID_MOA_TRACE, str(exc), None)
        )


def aggregate_trace_validations(values: tuple[TraceValidation, ...]) -> dict[str, int]:
    usages = [value.usage for value in values if value.usage is not None]
    return {
        "valid": len(usages),
        "excluded": len(values) - len(usages),
        "reference_calls": sum(v.reference_calls for v in usages),
        "reference_input_tokens": sum(v.reference_input_tokens for v in usages),
        "reference_output_tokens": sum(v.reference_output_tokens for v in usages),
    }
