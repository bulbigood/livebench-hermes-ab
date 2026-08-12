from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .core import ContractError, canonical_json, sha256_bytes


def _text_hash(text: str) -> str:
    return sha256_bytes(text.strip().encode())


def validate_moa_trace_record(
    record: dict[str, Any],
    answer: str,
    hermes_config: dict[str, Any],
) -> dict[str, int]:
    moa = hermes_config.get("moa", {})
    preset_name = str(moa.get("active_preset") or moa.get("default_preset") or "default")
    preset = moa.get("presets", {}).get(preset_name, {})
    expected_references = list(preset.get("reference_models") or [])
    expected_aggregator = dict(preset.get("aggregator") or {})
    if record.get("preset") != preset_name:
        raise ContractError("unexpected preset")
    references = record.get("references") or []
    if len(references) != len(expected_references):
        raise ContractError("unexpected reference count")
    reference_input = reference_output = 0
    for reference, expected_reference in zip(references, expected_references, strict=True):
        if reference.get("provider") != expected_reference.get("provider"):
            raise ContractError("unexpected reference provider")
        if reference.get("model") != expected_reference.get("model"):
            raise ContractError("unexpected reference model")
        output = str(reference.get("output") or "").strip()
        if not output:
            raise ContractError("empty reference output")
        if output.casefold() == "(empty response)":
            raise ContractError("degraded reference output")
        usage = reference.get("usage") or {}
        if int(usage.get("output_tokens") or 0) <= 0:
            raise ContractError("missing reference output usage")
        reference_input += int(usage.get("input_tokens") or 0)
        reference_output += int(usage.get("output_tokens") or 0)
    aggregator = record.get("aggregator") or {}
    if aggregator.get("provider") != expected_aggregator.get("provider"):
        raise ContractError("unexpected aggregator provider")
    if aggregator.get("model") != expected_aggregator.get("model"):
        raise ContractError("unexpected aggregator model")
    aggregate_output = str(aggregator.get("output") or "").strip()
    if not aggregate_output:
        raise ContractError("empty aggregator output")
    if _text_hash(aggregate_output) != _text_hash(answer):
        raise ContractError("MoA trace output does not match persisted answer")
    return {
        "reference_input_tokens": reference_input,
        "reference_output_tokens": reference_output,
    }


def validate_moa_traces(
    run_dir: Path,
    expected_count: int,
    arm_name: str = "moa",
    hermes_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace_dir = run_dir / "homes" / arm_name / "moa-traces"
    preset_name = "default"
    expected_references = [{"provider": "openrouter", "model": "minimax/minimax-m3"}]
    expected_aggregator = {"provider": "openai-codex", "model": "gpt-5.6-sol"}
    if hermes_config is not None:
        moa = hermes_config.get("moa", {})
        preset_name = str(moa.get("active_preset") or moa.get("default_preset") or "default")
        preset = moa.get("presets", {}).get(preset_name, {})
        expected_references = list(preset.get("reference_models") or [])
        expected_aggregator = dict(preset.get("aggregator") or {})
    paths = sorted(trace_dir.glob("*.jsonl")) if trace_dir.is_dir() else []
    records: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
    if len(records) != expected_count:
        raise ContractError(
            f"MoA trace cardinality mismatch: expected {expected_count}, got {len(records)}"
        )

    answer_path = run_dir / "raw" / f"hermes-{arm_name}.jsonl"
    answer_hashes: list[str] = []
    with answer_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            turns = row["choices"][0]["turns"]
            if len(turns) != 1 or not str(turns[0]).strip():
                raise ContractError("MoA answer is empty or not single-turn")
            answer_hashes.append(_text_hash(str(turns[0])))

    trace_output_hashes: list[str] = []
    reference_input = reference_output = 0
    for index, record in enumerate(records):
        if record.get("preset") != preset_name:
            raise ContractError(f"trace {index}: unexpected preset")
        references = record.get("references") or []
        if len(references) != len(expected_references):
            raise ContractError(f"trace {index}: unexpected reference count")
        for reference, expected_reference in zip(references, expected_references, strict=True):
            if reference.get("provider") != expected_reference.get("provider"):
                raise ContractError(f"trace {index}: unexpected reference provider")
            if reference.get("model") != expected_reference.get("model"):
                raise ContractError(f"trace {index}: unexpected reference model")
            reference_output_text = str(reference.get("output") or "").strip()
            if not reference_output_text:
                raise ContractError(f"trace {index}: empty reference output")
            if reference_output_text.casefold() == "(empty response)":
                raise ContractError(f"trace {index}: degraded reference output")
            usage = reference.get("usage") or {}
            if int(usage.get("output_tokens") or 0) <= 0:
                raise ContractError(f"trace {index}: missing reference output usage")
            reference_input += int(usage.get("input_tokens") or 0)
            reference_output += int(usage.get("output_tokens") or 0)

        aggregator = record.get("aggregator") or {}
        if aggregator.get("provider") != expected_aggregator.get("provider"):
            raise ContractError(f"trace {index}: unexpected aggregator provider")
        if aggregator.get("model") != expected_aggregator.get("model"):
            raise ContractError(f"trace {index}: unexpected aggregator model")
        output = str(aggregator.get("output") or "")
        if not output.strip():
            raise ContractError(f"trace {index}: empty aggregator output")
        trace_output_hashes.append(_text_hash(output))

    if Counter(answer_hashes) != Counter(trace_output_hashes):
        raise ContractError("MoA trace outputs do not match persisted answers")

    audit = {
        "status": "valid",
        "trace_records": len(records),
        "arm": arm_name,
        "reference_calls": len(records) * len(expected_references),
        "reference_models": expected_references,
        "reference_input_tokens": reference_input,
        "reference_output_tokens": reference_output,
        "aggregator_provider": expected_aggregator.get("provider"),
        "aggregator_model": expected_aggregator.get("model"),
        "answer_trace_hashes_match": True,
    }
    audit_name = "trace-audit.json" if arm_name == "moa" else f"trace-audit-{arm_name}.json"
    (run_dir / audit_name).write_bytes(canonical_json(audit) + b"\n")
    return audit
