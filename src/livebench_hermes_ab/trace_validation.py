from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .core import ContractError, canonical_json, sha256_bytes


def _text_hash(text: str) -> str:
    return sha256_bytes(text.strip().encode())


def validate_moa_traces(run_dir: Path, expected_count: int) -> dict[str, Any]:
    trace_dir = run_dir / "homes" / "moa" / "moa-traces"
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

    answer_path = run_dir / "raw" / "hermes-moa.jsonl"
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
        if record.get("preset") != "default":
            raise ContractError(f"trace {index}: unexpected preset")
        references = record.get("references") or []
        if len(references) != 1:
            raise ContractError(f"trace {index}: expected exactly one reference")
        reference = references[0]
        if reference.get("provider") != "openrouter":
            raise ContractError(f"trace {index}: unexpected reference provider")
        if reference.get("model") != "minimax/minimax-m3":
            raise ContractError(f"trace {index}: unexpected reference model")
        if not str(reference.get("output") or "").strip():
            raise ContractError(f"trace {index}: empty reference output")
        usage = reference.get("usage") or {}
        if int(usage.get("output_tokens") or 0) <= 0:
            raise ContractError(f"trace {index}: missing reference output usage")
        reference_input += int(usage.get("input_tokens") or 0)
        reference_output += int(usage.get("output_tokens") or 0)

        aggregator = record.get("aggregator") or {}
        if aggregator.get("provider") != "openai-codex":
            raise ContractError(f"trace {index}: unexpected aggregator provider")
        if aggregator.get("model") != "gpt-5.6-sol":
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
        "reference_calls": len(records),
        "reference_provider": "openrouter",
        "reference_model": "minimax/minimax-m3",
        "reference_input_tokens": reference_input,
        "reference_output_tokens": reference_output,
        "aggregator_provider": "openai-codex",
        "aggregator_model": "gpt-5.6-sol",
        "answer_trace_hashes_match": True,
    }
    (run_dir / "trace-audit.json").write_bytes(canonical_json(audit) + b"\n")
    return audit
