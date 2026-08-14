from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

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
class ProviderCallRecord:
    role: Literal["reference", "aggregator", "acting"]
    provider: str
    model: str
    status: str
    input_tokens: int | None
    output_tokens: int | None
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    reasoning_tokens: int | None
    estimated_cost_usd: float | None
    actual_cost_usd: float | None
    cost_status: str | None
    cost_source: str | None
    generation_id: str | None
    usage_complete: bool
    cost_complete: bool

    def as_dict(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True)
class TraceValidation:
    usage: TraceUsage | None
    exclusion: ExcludedOutcome | None
    sanitized_trace: dict[str, object] | None = None
    provider_calls: tuple[ProviderCallRecord, ...] = ()


def _hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode()).hexdigest()


_SECRET_KEYS = {
    "api_key", "apikey", "authorization", "cookie", "credentials", "password",
    "refresh_token", "access_token", "secret", "token",
}
_BEARER = re.compile(r"(?i)(authorization\s*:\s*)?bearer\s+[A-Za-z0-9._~+/=-]+")


def _sanitize(value: Any, key: str | None = None) -> Any:
    normalized = (key or "").casefold().replace("-", "_")
    if normalized in _SECRET_KEYS or normalized.endswith(("_api_key", "_secret")):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(child_key): _sanitize(child, str(child_key)) for child_key, child in value.items()}
    if isinstance(value, list):
        return [_sanitize(child) for child in value]
    if isinstance(value, str):
        return _BEARER.sub("[REDACTED]", value)
    return value


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _provider_call(role: Literal["reference", "aggregator", "acting"], value: object,
                   status: str) -> ProviderCallRecord | None:
    if not isinstance(value, dict):
        return None
    raw_usage = value.get("usage")
    usage: dict[str, object] = dict(raw_usage) if isinstance(raw_usage, dict) else {}
    input_tokens = _int_or_none(usage.get("input_tokens"))
    output_tokens = _int_or_none(usage.get("output_tokens"))
    estimated = _float_or_none(value.get("estimated_cost_usd", value.get("cost_usd")))
    actual = _float_or_none(value.get("actual_cost_usd"))
    return ProviderCallRecord(
        role=role,
        provider=str(value.get("provider") or "unknown"),
        model=str(value.get("model") or "unknown"),
        status=status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=_int_or_none(usage.get("cache_read_tokens")),
        cache_write_tokens=_int_or_none(usage.get("cache_write_tokens")),
        reasoning_tokens=_int_or_none(usage.get("reasoning_tokens")),
        estimated_cost_usd=estimated,
        actual_cost_usd=actual,
        cost_status=str(value.get("cost_status")) if value.get("cost_status") is not None else None,
        cost_source=str(value.get("cost_source")) if value.get("cost_source") is not None else None,
        generation_id=str(value.get("generation_id")) if value.get("generation_id") is not None else None,
        usage_complete=input_tokens is not None and output_tokens is not None,
        cost_complete=actual is not None or estimated is not None,
    )


def _calls(record: object, status: str) -> tuple[ProviderCallRecord, ...]:
    if not isinstance(record, dict):
        return ()
    values: list[ProviderCallRecord] = []
    references = record.get("references")
    if isinstance(references, list):
        values.extend(
            call for item in references
            if (call := _provider_call("reference", item, status)) is not None
        )
    aggregator = _provider_call("aggregator", record.get("aggregator"), status)
    if aggregator is not None:
        values.append(aggregator)
    return tuple(values)


def validate_cell_trace(
    trace_bytes: bytes, expected: ExpectedTrace, answer: str
) -> TraceValidation:
    record: object = None
    sanitized: dict[str, object] | None = None
    calls: tuple[ProviderCallRecord, ...] = ()
    try:
        lines = [json.loads(line) for line in trace_bytes.splitlines() if line.strip()]
        if len(lines) != 1:
            raise ValueError("expected exactly one trace record")
        record = lines[0]
        if not isinstance(record, dict):
            raise TypeError("trace record must be an object")
        sanitized = _sanitize(record)
        calls = _calls(record, "succeeded")
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
        return TraceValidation(
            TraceUsage(input_tokens, output_tokens, len(references)), None, sanitized, calls
        )
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(record, dict):
            sanitized = _sanitize(record)
            calls = _calls(record, "invalid_trace")
        return TraceValidation(
            None,
            ExcludedOutcome(expected.cell, ExclusionCode.INVALID_MOA_TRACE, str(exc), None),
            sanitized,
            calls,
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
