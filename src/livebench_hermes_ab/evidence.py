from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence

from .domain import CellOutcome, ValidOutcome

ScoreAdapter = Callable[[Mapping[str, object], str], float]

_CANDIDATE = re.compile(r"(?im)^\s*CANDIDATE:\s*(.+?)\s*$")
_UNDERDETERMINED = re.compile(
    r"\b(?:underdetermined|insufficient information|cannot determine|not enough information|ambiguous)\b",
    re.IGNORECASE,
)
_STRUCTURAL_VIOLATION = re.compile(
    r"(?:<tool|tool_call|ignore (?:all )?(?:previous|prior) instructions|you are now|^\s*(?:system|assistant):)",
    re.IGNORECASE | re.MULTILINE,
)


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _traces(outcome: ValidOutcome) -> list[Mapping[str, object]]:
    record = outcome.answer_record
    direct = record.get("moa_traces")
    if isinstance(direct, (list, tuple)):
        values = [value for value in direct if isinstance(value, Mapping)]
        if values:
            return values
    single = record.get("moa_trace")
    if isinstance(single, Mapping):
        return [single]
    traces: list[Mapping[str, object]] = []
    audits = record.get("trace_audit")
    if not isinstance(audits, (list, tuple)):
        return traces
    for audit in audits:
        if not isinstance(audit, Mapping):
            continue
        trace_record = audit.get("trace_record")
        if isinstance(trace_record, Mapping):
            traces.append(trace_record)
            continue
        raw = audit.get("trace")
        if not isinstance(raw, str):
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, Mapping):
            traces.append(parsed)
    return traces


def _trace_calls(trace: Mapping[str, object]) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    references = trace.get("references")
    if isinstance(references, list):
        for reference in references:
            if isinstance(reference, Mapping):
                calls.append(_call_value(reference, "reference"))
    aggregator = trace.get("aggregator")
    if isinstance(aggregator, Mapping):
        calls.append(_call_value(aggregator, "aggregator"))
    return calls


def _number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _call_value(value: Mapping[str, object], role: str) -> dict[str, object]:
    usage = _mapping(value.get("usage")) or {}
    input_tokens = _number(usage.get("input_tokens"))
    output_tokens = _number(usage.get("output_tokens"))
    estimated = _number(value.get("estimated_cost_usd"))
    if estimated is None:
        estimated = _number(value.get("cost_usd"))
    actual = _number(value.get("actual_cost_usd"))
    return {
        "role": role,
        "provider": str(value.get("provider") or "unknown"),
        "model": str(value.get("model") or "unknown"),
        "status": str(value.get("status") or "succeeded"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": _number(usage.get("cache_read_tokens")),
        "cache_write_tokens": _number(usage.get("cache_write_tokens")),
        "reasoning_tokens": _number(usage.get("reasoning_tokens")),
        "estimated_cost_usd": estimated,
        "actual_cost_usd": actual,
        "cost_status": value.get("cost_status"),
        "cost_source": value.get("cost_source"),
        "generation_id": value.get("generation_id") or value.get("id"),
        "usage_complete": input_tokens is not None and output_tokens is not None,
        "cost_complete": estimated is not None or actual is not None,
    }


def outcome_provider_calls(outcome: CellOutcome) -> list[dict[str, object]]:
    source: object = (
        outcome.answer_record.get("provider_calls")
        if isinstance(outcome, ValidOutcome)
        else outcome.evidence.get("provider_calls") if outcome.evidence is not None else None
    )
    if isinstance(source, (list, tuple)):
        calls = [dict(value) for value in source if isinstance(value, Mapping)]
        if calls:
            return calls
    if isinstance(outcome, ValidOutcome):
        return [call for trace in _traces(outcome) for call in _trace_calls(trace)]
    return []


def billing_summary(
    evidence: Sequence[CellOutcome], *, source: str = "terminal_outcomes"
) -> dict[str, object]:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    cells_without_ledger = 0
    for outcome in evidence:
        calls = outcome_provider_calls(outcome)
        if not calls:
            cells_without_ledger += 1
        for call in calls:
            key = (
                outcome.cell.arm,
                str(call.get("role") or "unknown"),
                str(call.get("provider") or "unknown"),
                str(call.get("model") or "unknown"),
                str(call.get("status") or "unknown"),
            )
            groups[key].append(call)

    rows: list[dict[str, object]] = []
    all_calls = [call for calls in groups.values() for call in calls]
    token_fields = (
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
    )
    for (arm, role, provider, model, status), calls in sorted(groups.items()):
        row: dict[str, object] = {
            "arm": arm,
            "stage": role,
            "role": role,
            "provider": provider,
            "model": model,
            "status": status,
            "calls": len(calls),
            "usage_complete_calls": sum(bool(call.get("usage_complete")) for call in calls),
            "cost_complete_calls": sum(bool(call.get("cost_complete")) for call in calls),
            "generation_id_calls": sum(bool(call.get("generation_id")) for call in calls),
        }
        for field in token_fields:
            row[field] = sum(int(call.get(field) or 0) for call in calls)
        row["estimated_cost_usd"] = sum(float(call.get("estimated_cost_usd") or 0) for call in calls)
        row["actual_cost_usd"] = sum(float(call.get("actual_cost_usd") or 0) for call in calls)
        rows.append(row)
    result: dict[str, object] = {
        "source": source,
        "evidence_records": len(evidence),
        "recorded_calls": len(all_calls),
        "cells_without_provider_ledger": cells_without_ledger,
        "usage_complete_calls": sum(bool(call.get("usage_complete")) for call in all_calls),
        "cost_complete_calls": sum(bool(call.get("cost_complete")) for call in all_calls),
        "generation_id_calls": sum(bool(call.get("generation_id")) for call in all_calls),
        "groups": rows,
    }
    for field in token_fields:
        result[field] = sum(int(call.get(field) or 0) for call in all_calls)
    result["estimated_cost_usd"] = sum(
        float(call.get("estimated_cost_usd") or 0) for call in all_calls
    )
    result["actual_cost_usd"] = sum(float(call.get("actual_cost_usd") or 0) for call in all_calls)
    result["complete"] = (
        cells_without_ledger == 0
        and result["usage_complete_calls"] == len(all_calls)
        and result["cost_complete_calls"] == len(all_calls)
        and result["generation_id_calls"] == len(all_calls)
    )
    return result


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def mechanism_summary(
    outcomes: Sequence[CellOutcome],
    questions: Mapping[str, object],
    adapters: Mapping[str, ScoreAdapter],
) -> dict[str, object]:
    accumulators: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    full_trace_cells = 0
    for outcome in outcomes:
        if not isinstance(outcome, ValidOutcome):
            continue
        traces = _traces(outcome)
        if not traces:
            continue
        full_trace_cells += 1
        final_answer = str(outcome.answer_record.get("answer") or "")
        question = questions.get(outcome.cell.question_id)
        task = getattr(question, "task", None)
        raw = getattr(question, "raw", None)
        adapter = adapters.get(task) if isinstance(task, str) else None
        bucket = accumulators[outcome.cell.arm]
        bucket["trace_cells"] += 1
        for trace in traces:
            references = trace.get("references")
            references = references if isinstance(references, list) else []
            outputs = [
                str(reference.get("output") or "")
                for reference in references
                if isinstance(reference, Mapping)
            ]
            bucket["reference_outputs"] += len(outputs)
            bucket["duplicate_reference_outputs"] += len(outputs) - len(
                {_normalized(output) for output in outputs}
            )
            aggregator = trace.get("aggregator")
            aggregator = aggregator if isinstance(aggregator, Mapping) else {}
            messages = json.dumps(aggregator.get("messages") or [], ensure_ascii=False)
            if "<BEGIN_UNTRUSTED_REFERENCE_BLOCKS>" in messages and "<END_UNTRUSTED_REFERENCE_BLOCKS>" in messages:
                bucket["untrusted_wrapper_present"] += 1
            for output in outputs:
                bucket["structural_violation_outputs"] += bool(_STRUCTURAL_VIOLATION.search(output))
                bucket["underdetermination_signal_outputs"] += bool(_UNDERDETERMINED.search(output))
                match = _CANDIDATE.search(output)
                if not match:
                    continue
                candidate = match.group(1).strip()
                if not candidate or candidate.casefold() in {"none", "n/a", "unknown"}:
                    continue
                bucket["candidate_present"] += 1
                adopted = _normalized(candidate) in _normalized(final_answer)
                bucket["candidate_exact_adoption"] += adopted
                if adapter is None or not isinstance(raw, Mapping):
                    continue
                try:
                    candidate_score = float(adapter(raw, candidate))
                except (KeyError, TypeError, ValueError, IndexError):
                    continue
                bucket["candidate_scorable"] += 1
                bucket["candidate_score_sum"] += candidate_score
                bucket["candidate_full_correct"] += candidate_score == 1.0
                bucket["useful_candidate_adoption"] += adopted and candidate_score > 0
                bucket["erroneous_candidate_adoption"] += adopted and candidate_score <= 0
    by_arm: dict[str, object] = {}
    for arm, raw_values in sorted(accumulators.items()):
        values: dict[str, object] = {key: int(value) for key, value in raw_values.items()}
        scorable = int(raw_values.get("candidate_scorable", 0))
        values["candidate_score_mean"] = (
            raw_values.get("candidate_score_sum", 0.0) / scorable if scorable else None
        )
        values.pop("candidate_score_sum", None)
        by_arm[arm] = values
    return {
        "schema_version": 1,
        "full_trace_cells": full_trace_cells,
        "semantic_claim_annotations_available": False,
        "proxy_warning": (
            "candidate adoption is normalized substring matching; erroneous/useful adoption uses "
            "the objective candidate score and is not claim-level semantic annotation"
        ),
        "by_arm": by_arm,
    }
