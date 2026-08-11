from __future__ import annotations

import hashlib
import json
import random
import re
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


def build_command(
    arm_name: str,
    arm: dict[str, Any],
    prompt: str,
    *,
    executable: str = "hermes",
) -> list[str]:
    hermes = arm.get("hermes")
    if hermes is not None:
        provider = hermes["model"]["provider"]
        model = hermes["model"]["default"]
    else:
        provider = arm["provider"]
        model = arm["model"]
    return [
        executable,
        "--ignore-rules",
        "--oneshot",
        prompt,
        "--provider",
        str(provider),
        "--model",
        str(model),
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


def resolve_explicit_scenarios(
    questions: list[dict[str, Any]], selection: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Resolve one experiment-global scenario list against the pinned corpus."""

    has_flat = "question_ids" in selection
    has_grouped = "scenarios" in selection
    if has_flat == has_grouped:
        raise ContractError("selection must define exactly one of question_ids or scenarios")

    specs: list[dict[str, str]] = []
    if has_flat:
        values = selection["question_ids"]
        if not isinstance(values, list) or not values:
            raise ContractError("selection.question_ids must be a non-empty list")
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ContractError("selection.question_ids entries must be non-empty strings")
            specs.append({"id": value})
    else:
        groups = selection["scenarios"]
        if not isinstance(groups, dict) or not groups:
            raise ContractError("selection.scenarios must be a non-empty category mapping")
        allowed_keys = {"id", "family", "source_url", "note"}
        for category, entries in groups.items():
            if not isinstance(category, str) or not category.strip():
                raise ContractError("scenario category names must be non-empty strings")
            if not isinstance(entries, list) or not entries:
                raise ContractError(f"selection.scenarios.{category} must be a non-empty list")
            for index, entry in enumerate(entries):
                path = f"selection.scenarios.{category}[{index}]"
                if not isinstance(entry, dict):
                    raise ContractError(f"{path} must be a mapping")
                unknown = sorted(set(entry) - allowed_keys)
                if unknown:
                    raise ContractError(f"{path} contains unsupported keys: {unknown}")
                scenario_id = entry.get("id")
                family = entry.get("family")
                if not isinstance(scenario_id, str) or not scenario_id.strip():
                    raise ContractError(f"{path}.id must be a non-empty string")
                if not isinstance(family, str) or not family.strip():
                    raise ContractError(f"{path}.family must be a non-empty string")
                spec = {"id": scenario_id, "category": category, "family": family}
                for metadata_key in ("source_url", "note"):
                    if metadata_key not in entry:
                        continue
                    metadata = entry[metadata_key]
                    if not isinstance(metadata, str) or not metadata.strip():
                        raise ContractError(f"{path}.{metadata_key} must be a non-empty string")
                    if metadata_key == "source_url" and not re.fullmatch(r"https?://\S+", metadata):
                        raise ContractError(f"{path}.source_url must be an HTTP(S) URL")
                    spec[metadata_key] = metadata
                specs.append(spec)

    scenario_ids = [spec["id"] for spec in specs]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ContractError("selection contains duplicate scenario IDs")
    by_question_id = {str(question["question_id"]): question for question in questions}
    missing = [scenario_id for scenario_id in scenario_ids if scenario_id not in by_question_id]
    if missing:
        raise ContractError(f"selected scenario IDs unavailable: {missing}")

    selected: list[dict[str, Any]] = []
    resolved: list[dict[str, str]] = []
    for spec in specs:
        question = by_question_id[spec["id"]]
        actual_category = str(question.get("category"))
        actual_family = str(question.get("task"))
        if "category" in spec and spec["category"] != actual_category:
            raise ContractError(
                f"scenario {spec['id']} category mismatch: configured {spec['category']}, "
                f"corpus has {actual_category}"
            )
        if "family" in spec and spec["family"] != actual_family:
            raise ContractError(
                f"scenario {spec['id']} family mismatch: configured {spec['family']}, "
                f"corpus has {actual_family}"
            )
        metadata = {"id": spec["id"], "category": actual_category, "family": actual_family}
        metadata.update({key: spec[key] for key in ("source_url", "note") if key in spec})
        selected.append(question)
        resolved.append(metadata)
    return selected, resolved


def validate_frozen_selection(selected: list[dict[str, Any]], selection: dict[str, Any]) -> None:
    if "new_task_count" in selection and len(selected) != int(selection["new_task_count"]):
        raise ContractError("new_task_count does not match frozen question IDs")
    expected_counts = selection.get("category_task_counts")
    if expected_counts is not None:
        actual_counts = {
            category: sum(q.get("category") == category for q in selected)
            for category in sorted({str(q.get("category")) for q in selected})
        }
        normalized_expected = {
            str(category): int(count) for category, count in expected_counts.items()
        }
        if actual_counts != normalized_expected:
            raise ContractError(
                f"category task cardinality mismatch: expected {normalized_expected}, "
                f"got {actual_counts}"
            )
    elif "math_task_count" in selection:
        math_count = sum(q.get("category") == "math" for q in selected)
        if math_count != int(selection["math_task_count"]):
            raise ContractError("math task cardinality mismatch")
    expected_families = selection.get("task_family_counts")
    if expected_families is not None:
        actual_families: dict[str, dict[str, int]] = {}
        for question in selected:
            category = str(question.get("category"))
            task = str(question.get("task"))
            family_counts = actual_families.setdefault(category, {})
            family_counts[task] = family_counts.get(task, 0) + 1
        normalized_families = {
            str(category): {str(task): int(count) for task, count in tasks.items()}
            for category, tasks in expected_families.items()
        }
        if actual_families != normalized_families:
            raise ContractError(
                f"task family cardinality mismatch: expected {normalized_families}, "
                f"got {actual_families}"
            )


def make_pairs(
    questions: list[dict[str, Any]],
    seed: int,
    samples_per_task: int = 1,
    arms: list[str] | None = None,
) -> list[dict[str, Any]]:
    arm_names = arms or ["base", "moa"]
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
                "order": arm_names[idx % len(arm_names) :] + arm_names[: idx % len(arm_names)],
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
