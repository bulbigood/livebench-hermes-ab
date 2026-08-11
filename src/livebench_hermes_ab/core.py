from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def validate_treatment_boundary(config: dict[str, Any]) -> None:
    arms = config.get("arms", {})
    if set(arms) != {"base", "moa"}:
        raise ContractError("arms must be exactly base and moa")
    base, moa = arms["base"], arms["moa"]
    agg = moa.get("aggregator", {})
    for key in ("provider", "model", "reasoning_effort"):
        if base.get(key) != agg.get(key):
            raise ContractError(f"BASE and MoA aggregator differ at {key}")
    if base.get("reasoning_effort") not in {"low", "medium"}:
        raise ContractError("unsupported reasoning effort")
    if moa.get("reasoning_effort") != base.get("reasoning_effort"):
        raise ContractError("both arms must use identical reasoning")
    if base.get("moa_enabled") is not False or moa.get("moa_enabled") is not True:
        raise ContractError("MoA must be the only treatment")
    if moa.get("provider") != "moa" or moa.get("preset") != moa.get("model"):
        raise ContractError("MoA provider/model must name the configured preset")
    refs = moa.get("references")
    if refs != [{"provider": "openrouter", "model": "minimax/minimax-m3"}]:
        raise ContractError("references must be exactly OpenRouter Minimax M3")


def build_prompt(question: dict[str, Any], prior_answers: list[str]) -> str:
    turns = question.get("turns")
    if not isinstance(turns, list) or not turns or not all(isinstance(x, str) for x in turns):
        raise ContractError(f"invalid turns for {question.get('question_id')}")
    turn_index = len(prior_answers)
    if turn_index >= len(turns):
        raise ContractError("more prior answers than question turns")
    chunks: list[str] = []
    if question.get("system_prompt"):
        chunks.append(str(question["system_prompt"]))
    for idx in range(turn_index):
        chunks.extend([turns[idx], "Assistant's previous response:\n" + prior_answers[idx]])
    chunks.append(turns[turn_index])
    return "\n\n".join(chunks)


def build_command(arm_name: str, arm: dict[str, Any], prompt: str) -> list[str]:
    if arm_name not in {"base", "moa"}:
        raise ContractError(f"unknown arm {arm_name}")
    return [
        "hermes",
        "--ignore-rules",
        "--oneshot",
        prompt,
        "--provider",
        str(arm["provider"]),
        "--model",
        str(arm["model"]),
    ]


def select_stratified_complexity(
    questions: list[dict[str, Any]], categories: list[str], seed: int
) -> list[dict[str, Any]]:
    """Select one demanding question per category without looking at answers."""

    def rank(q: dict[str, Any]) -> tuple[int, int, int, int, str]:
        constraints = len(q.get("instruction_id_list") or [])
        turns = len(q.get("turns") or [])
        prompt_chars = sum(len(str(turn)) for turn in q.get("turns") or [])
        raw_level = q.get("level", q.get("hardness", 0))
        try:
            level = int(raw_level)
        except (TypeError, ValueError):
            level = 0
        tie = sha256_bytes(f"{seed}:{q['question_id']}".encode())
        return level, constraints, turns, prompt_chars, tie

    chosen: list[dict[str, Any]] = []
    for category in categories:
        candidates = [q for q in questions if q.get("category") == category]
        if not candidates:
            raise ContractError(f"no active questions for selection category {category}")
        chosen.append(max(candidates, key=rank))
    return chosen


def make_pairs(
    questions: list[dict[str, Any]], seed: int, samples_per_task: int = 1
) -> list[dict[str, Any]]:
    if samples_per_task < 1:
        raise ContractError("samples_per_task must be positive")
    ordered = [
        (question, sample_index)
        for question in sorted(questions, key=lambda q: str(q["question_id"]))
        for sample_index in range(samples_per_task)
    ]
    rng = random.Random(seed)
    rng.shuffle(ordered)
    result = []
    for idx, (question, sample_index) in enumerate(ordered):
        qid = str(question["question_id"])
        result.append(
            {
                "pair_id": sha256_bytes(f"{seed}:{qid}:{sample_index}".encode())[:16],
                "question_id": qid,
                "sample_index": sample_index,
                "order": ["base", "moa"] if idx % 2 == 0 else ["moa", "base"],
            }
        )
    return result


def load_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(paths):
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                qid = str(row.get("question_id", ""))
                if not qid or qid in seen:
                    raise ContractError(f"missing/duplicate question_id at {path}:{line_no}: {qid}")
                build_prompt(row, [])
                row["_source_file"] = str(path)
                seen.add(qid)
                rows.append(row)
    return rows


def filter_livebench_snapshot(
    questions: list[dict[str, Any]], release_cutoff: str, allowed_releases: set[str]
) -> list[dict[str, Any]]:
    """Mirror LiveBench's JSONL snapshot semantics from common.py."""
    return [
        q
        for q in questions
        if q.get("livebench_release_date") in allowed_releases
        and (
            not str(q.get("livebench_removal_date", ""))
            or str(q["livebench_removal_date"]) > release_cutoff
        )
    ]
