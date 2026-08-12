from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .core import ContractError, canonical_json, sha256_bytes
from .trace_validation import validate_moa_trace_record


def summary_status(manifest: dict[str, Any], excluded: bool) -> str:
    compatibility_status = manifest.get("hermes_compatibility", {}).get("status")
    hermes_warning = compatibility_status != "verified"
    if excluded and hermes_warning:
        return "VALID_WITH_ONE_INFRA_EXCLUSION_AND_HERMES_WARNING"
    if excluded:
        return "VALID_WITH_ONE_INFRA_EXCLUSION"
    if hermes_warning:
        return "VALID_WITH_HERMES_WARNING"
    return "VALID"


def timing_summary(
    manifest: dict[str, Any],
    answers_by_arm: dict[str, Any],
) -> dict[str, Any]:
    execution = manifest.get("execution_contract", {})
    comparable = bool(execution.get("timing_comparable", False))
    arms: dict[str, dict[str, float | int]] = {}
    for arm_name, rows in answers_by_arm.items():
        iterable = rows.values() if isinstance(rows, dict) else rows
        values = [
            float(row["total_time_s"]) for row in iterable if row.get("total_time_s") is not None
        ]
        if values:
            arms[arm_name] = {
                "samples": len(values),
                "mean_cell_seconds": sum(values) / len(values),
                "sum_cell_seconds": sum(values),
            }
    return {
        "scheduling": execution.get("scheduling", "legacy"),
        "effective_workers": execution.get("effective_workers"),
        "paired_wall_time_comparable": comparable,
        "marker": None if comparable else "*",
        "note": execution.get("timing_note"),
        "run_makespan_seconds": manifest.get("execution_result", {}).get("run_makespan_seconds"),
        "arms": arms,
    }


def summary_compatibility(manifest: dict[str, Any]) -> dict[str, Any]:
    report = manifest.get("hermes_compatibility", {})
    return {
        key: report[key]
        for key in (
            "status",
            "profile",
            "version",
            "executable",
            "warning_codes",
            "warnings",
        )
        if key in report
    }


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "upstream"
if str(UPSTREAM) not in sys.path:
    sys.path.insert(0, str(UPSTREAM))


def _load_answers(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.is_file():
        raise ContractError(f"missing answer file: {path}")
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            qid = str(row["question_id"])
            sample_index = int(row.get("sample_index", 0))
            cell = (qid, sample_index)
            if cell in rows:
                raise ContractError(f"duplicate answer for {cell} in {path}")
            rows[cell] = row
    return rows


def answer_text(record: dict[str, Any]) -> str:
    turns = record["choices"][0]["turns"]
    if not turns or not str(turns[-1]).strip():
        raise ContractError("empty final answer")
    return str(turns[-1])


def score_standard(question: dict[str, Any], answer: str) -> float:
    task = str(question["task"])
    ground_truth = question.get("ground_truth")
    if task == "cta":
        from livebench.process_results.data_analysis.cta.utils import cta_process_results

        return float(cta_process_results(ground_truth, answer))
    if task == "zebra_puzzle":
        from livebench.process_results.reasoning.zebra_puzzle.utils import (
            get_zebra_puzzle_evaluator,
        )

        evaluator = get_zebra_puzzle_evaluator(str(question["livebench_release_date"]))
        return float(evaluator(ground_truth, answer))
    if task == "connections":
        from livebench.process_results.writing.connections.utils import (
            get_connections_puzzle_evaluator,
        )

        evaluator = get_connections_puzzle_evaluator(str(question["livebench_release_date"]))
        return float(evaluator(ground_truth, answer))
    if task == "olympiad":
        from livebench.process_results.math.olympiad.utils import (
            proof_rearrangement_process_results,
        )

        return float(
            proof_rearrangement_process_results(
                ground_truth, answer, edit_distance=True, debug=False
            )
        )
    if task == "math_comp":
        from livebench.process_results.math.math_competitions.utils import (
            aime_process_results,
            mathcontest_process_results,
        )

        subtask = str(question.get("subtask") or "")
        return (
            float(aime_process_results(ground_truth, answer, debug=False))
            if subtask.startswith("aime")
            else float(
                mathcontest_process_results(
                    ground_truth, answer, str(question["turns"][0]), debug=False
                )
            )
        )
    if task == "spatial":
        from livebench.process_results.reasoning.spatial.utils import spatial_process_results

        return float(spatial_process_results(ground_truth, answer, debug=False))
    if task == "tablejoin":
        from livebench.process_results.data_analysis.tablejoin.utils import joinmap_process_results

        return float(
            joinmap_process_results(str(question["turns"][0]), ground_truth, answer, debug=False)
        )
    if task == "tablereformat":
        from livebench.process_results.data_analysis.tablereformat.utils import (
            table_process_results,
        )

        version = "v2" if str(question["livebench_release_date"]) >= "2025-04-25" else "v1"
        return float(
            table_process_results(
                str(question["turns"][0]), ground_truth, answer, version, debug=False
            )
        )
    raise ContractError(f"unsupported objective scoring task: {task}")


def score_instruction_following(
    question: dict[str, Any], record: dict[str, Any], arm: str, output_dir: Path
) -> float:
    import nltk
    from livebench.if_runner.instruction_following_eval import evaluation_main

    nltk_cache = Path.home() / ".cache" / "nltk_data"
    if str(nltk_cache) not in nltk.data.path:
        nltk.data.path.insert(0, str(nltk_cache))
    for resource in ("tokenizers/punkt", "tokenizers/punkt_tab/english"):
        try:
            nltk.data.find(resource)
        except LookupError as exc:
            raise ContractError(
                f"missing NLTK scoring data; install punkt and punkt_tab in {nltk_cache}"
            ) from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    model_answers = {arm: {str(question["question_id"]): record}}
    result = evaluation_main.evaluator([question], model_answers, str(output_dir), arm)["strict"]
    if len(result) != 1:
        raise ContractError("instruction-following evaluator returned incomplete results")
    item = result[0]
    per_instruction = [1 if value else 0 for value in item.follow_instruction_list]
    if not per_instruction:
        raise ContractError("instruction-following evaluator returned no instruction statuses")
    return (
        (1 if item.follow_all_instructions else 0) + sum(per_instruction) / len(per_instruction)
    ) / 2


def score_run(run_dir: Path) -> dict[str, Any]:
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    by_id = {str(q["question_id"]): q for q in questions}
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    expected = {(str(p["question_id"]), int(p["sample_index"])) for p in manifest["pairs"]}
    amendment_path = run_dir / "run-amendment.json"
    excluded: set[tuple[str, int]] = set()
    if amendment_path.is_file():
        amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
        cells = amendment.get("excluded_cells") or []
        if amendment.get("status") != "VALID_WITH_ONE_INFRA_EXCLUSION" or len(cells) != 1:
            raise ContractError("unsupported run amendment")
        excluded = {(str(cells[0]["question_id"]), int(cells[0]["sample_index"]))}
        if not excluded.issubset(expected):
            raise ContractError("excluded cell is outside frozen matrix")
    effective = expected - excluded
    arm_names = list(manifest["arms"])
    if any("hermes" in arm for arm in manifest["arms"].values()):
        return score_multiarm_run(run_dir, by_id, manifest, expected, arm_names, excluded)
    records = {
        arm: _load_answers(run_dir / "raw" / f"hermes-{arm}.jsonl") for arm in ("base", "moa")
    }
    for arm, rows in records.items():
        if set(rows) != effective:
            raise ContractError(
                f"{arm} answer coverage mismatch: expected {len(effective)}, got {len(rows)}"
            )

    scores: list[dict[str, Any]] = []
    deltas: list[dict[str, Any]] = []
    by_category: dict[str, list[float]] = defaultdict(list)
    by_task: dict[str, list[float]] = defaultdict(list)
    for qid, sample_index in sorted(effective):
        question = by_id[qid]
        pair_scores: dict[str, float] = {}
        for arm in ("base", "moa"):
            record = records[arm][(qid, sample_index)]
            if question["category"] == "instruction_following":
                score = score_instruction_following(
                    question,
                    record,
                    f"{arm}-{sample_index}",
                    run_dir / "if-evaluator" / arm / str(sample_index),
                )
            else:
                score = score_standard(question, answer_text(record))
            pair_scores[arm] = score
            scores.append(
                {
                    "question_id": qid,
                    "sample_index": sample_index,
                    "category": question["category"],
                    "task": question["task"],
                    "arm": arm,
                    "score": score,
                }
            )
        delta = pair_scores["moa"] - pair_scores["base"]
        deltas.append(
            {
                "question_id": qid,
                "sample_index": sample_index,
                "category": question["category"],
                "task": question["task"],
                "base": pair_scores["base"],
                "moa": pair_scores["moa"],
                "delta": delta,
            }
        )
        by_category[str(question["category"])].append(delta)
        by_task[qid].append(delta)

    base_scores = [d["base"] for d in deltas]
    moa_scores = [d["moa"] for d in deltas]
    task_means = {qid: sum(vals) / len(vals) for qid, vals in sorted(by_task.items())}
    summary = {
        "status": summary_status(manifest, bool(excluded)),
        "hermes_compatibility": summary_compatibility(manifest),
        "planned_pairs": len(expected),
        "excluded_pairs": len(excluded),
        "scored_pairs": len(effective),
        "tasks": len(by_task),
        "samples_by_task": {qid: len(vals) for qid, vals in sorted(by_task.items())},
        "base_mean": sum(base_scores) / len(base_scores),
        "moa_mean": sum(moa_scores) / len(moa_scores),
        "sample_mean_delta": sum(d["delta"] for d in deltas) / len(deltas),
        "task_mean_delta": sum(task_means.values()) / len(task_means),
        "sample_wins_ties_regressions": {
            "wins": sum(d["delta"] > 0 for d in deltas),
            "ties": sum(d["delta"] == 0 for d in deltas),
            "regressions": sum(d["delta"] < 0 for d in deltas),
        },
        "task_wins_ties_regressions": {
            "wins": sum(v > 0 for v in task_means.values()),
            "ties": sum(v == 0 for v in task_means.values()),
            "regressions": sum(v < 0 for v in task_means.values()),
        },
        "category_mean_delta": {
            category: sum(values) / len(values) for category, values in sorted(by_category.items())
        },
        "task_mean_deltas": task_means,
        "scores_sha256": sha256_bytes(canonical_json(scores)),
    }
    (run_dir / "scores.json").write_bytes(canonical_json(scores) + b"\n")
    (run_dir / "paired-deltas.json").write_bytes(canonical_json(deltas) + b"\n")
    (run_dir / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return summary


def score_multiarm_run(
    run_dir: Path,
    by_id: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    expected: set[tuple[str, int]],
    arm_names: list[str],
    legacy_pair_exclusions: set[tuple[str, int]],
) -> dict[str, Any]:
    baseline = str(manifest["execution_contract"]["baseline_arm"])
    if baseline not in arm_names:
        raise ContractError(f"baseline arm is not configured: {baseline}")
    pair_ids = {
        (str(pair["question_id"]), int(pair["sample_index"])): str(pair["pair_id"])
        for pair in manifest["pairs"]
    }
    records = {arm: _load_answers(run_dir / "raw" / f"hermes-{arm}.jsonl") for arm in arm_names}
    explicit: dict[tuple[str, tuple[str, int]], dict[str, Any]] = {}
    for identity in legacy_pair_exclusions:
        for arm in arm_names:
            explicit[(arm, identity)] = {
                "arm": arm,
                "pair_id": pair_ids[identity],
                "question_id": identity[0],
                "sample_index": identity[1],
                "code": "LEGACY_PAIR_EXCLUSION",
                "reason": "authorized pair-wide exclusion from run-amendment.json",
            }
    exclusions_path = run_dir / "exclusions.json"
    if exclusions_path.is_file():
        payload = json.loads(exclusions_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ContractError("unsupported exclusions schema")
        for item in payload.get("excluded_cells") or []:
            arm = str(item.get("arm"))
            identity = (str(item.get("question_id")), int(item.get("sample_index")))
            if arm not in arm_names or identity not in expected:
                raise ContractError("excluded cell is outside frozen matrix")
            if str(item.get("pair_id")) != pair_ids[identity]:
                raise ContractError("excluded cell pair_id does not match frozen matrix")
            if not str(item.get("code") or "") or not str(item.get("reason") or ""):
                raise ContractError("excluded cell is missing code or reason")
            key = (arm, identity)
            if key in explicit:
                raise ContractError("duplicate excluded cell")
            explicit[key] = dict(item)

    unexplained: list[str] = []
    for arm, rows in records.items():
        extra = set(rows) - expected
        if extra:
            raise ContractError(f"{arm} has answers outside frozen matrix")
        for identity in expected - set(rows):
            if (arm, identity) not in explicit:
                unexplained.append(f"{arm}:{identity[0]}:{identity[1]}")
    if unexplained:
        raise ContractError(f"unexplained missing cells: {', '.join(sorted(unexplained))}")

    exclusions = dict(explicit)
    for arm_name, arm in manifest["arms"].items():
        hermes_config = arm.get("hermes") if isinstance(arm, dict) else None
        moa_config = hermes_config.get("moa", {}) if isinstance(hermes_config, dict) else {}
        if moa_config.get("enabled") is not True:
            continue
        trace_dir = run_dir / "homes" / str(arm_name) / "moa-traces"
        for identity, record in records[str(arm_name)].items():
            pair_id = pair_ids[identity]
            paths = sorted(trace_dir.glob(f"{pair_id}-*.jsonl")) if trace_dir.is_dir() else []
            if len(paths) != 1:
                exclusions[(str(arm_name), identity)] = {
                    "arm": str(arm_name),
                    "pair_id": pair_id,
                    "question_id": identity[0],
                    "sample_index": identity[1],
                    "code": "INVALID_MOA_TRACE",
                    "reason": f"expected one trace, got {len(paths)}",
                }
                continue
            try:
                trace_records = [
                    json.loads(line)
                    for line in paths[0].read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            except json.JSONDecodeError as error:
                exclusions[(str(arm_name), identity)] = {
                    "arm": str(arm_name),
                    "pair_id": pair_id,
                    "question_id": identity[0],
                    "sample_index": identity[1],
                    "code": "INVALID_MOA_TRACE",
                    "reason": f"malformed trace JSON: {error.msg}",
                }
                continue
            if len(trace_records) != 1:
                exclusions[(str(arm_name), identity)] = {
                    "arm": str(arm_name),
                    "pair_id": pair_id,
                    "question_id": identity[0],
                    "sample_index": identity[1],
                    "code": "INVALID_MOA_TRACE",
                    "reason": f"expected one trace record, got {len(trace_records)}",
                }
                continue
            try:
                validate_moa_trace_record(trace_records[0], answer_text(record), hermes_config)
            except ContractError as error:
                exclusions[(str(arm_name), identity)] = {
                    "arm": str(arm_name),
                    "pair_id": pair_id,
                    "question_id": identity[0],
                    "sample_index": identity[1],
                    "code": "INVALID_MOA_TRACE",
                    "reason": str(error),
                }

    valid_by_arm = {
        arm: set(records[arm])
        - {identity for excluded_arm, identity in exclusions if excluded_arm == arm}
        for arm in arm_names
    }
    common_valid = set.intersection(*(valid_by_arm[arm] for arm in arm_names))
    if not common_valid:
        raise ContractError("no common valid pairs remain after exclusions")

    scores: list[dict[str, Any]] = []
    cells: list[dict[str, Any]] = []
    values_by_arm: dict[str, list[float]] = {arm: [] for arm in arm_names}
    task_values: dict[str, dict[str, list[float]]] = {arm: defaultdict(list) for arm in arm_names}
    category_values: dict[str, dict[str, list[float]]] = {
        arm: defaultdict(list) for arm in arm_names
    }
    for qid, sample_index in sorted(common_valid):
        question = by_id[qid]
        cell_scores: dict[str, float] = {}
        for arm in arm_names:
            record = records[arm][(qid, sample_index)]
            if question["category"] == "instruction_following":
                score = score_instruction_following(
                    question,
                    record,
                    f"{arm}-{sample_index}",
                    run_dir / "if-evaluator" / arm / str(sample_index),
                )
            else:
                score = score_standard(question, answer_text(record))
            cell_scores[arm] = score
            values_by_arm[arm].append(score)
            task_values[arm][qid].append(score)
            category_values[arm][str(question["category"])].append(score)
            scores.append(
                {
                    "question_id": qid,
                    "sample_index": sample_index,
                    "category": question["category"],
                    "task": question["task"],
                    "arm": arm,
                    "score": score,
                }
            )
        cells.append(
            {
                "question_id": qid,
                "sample_index": sample_index,
                "scores": cell_scores,
                "deltas_vs_baseline": {
                    arm: cell_scores[arm] - cell_scores[baseline]
                    for arm in arm_names
                    if arm != baseline
                },
            }
        )

    arm_means = {arm: sum(values) / len(values) for arm, values in values_by_arm.items()}
    comparisons = {}
    for arm in arm_names:
        if arm == baseline:
            continue
        sample_deltas = [cell["deltas_vs_baseline"][arm] for cell in cells]
        per_task_deltas = []
        for qid in sorted(task_values[baseline]):
            base_mean = sum(task_values[baseline][qid]) / len(task_values[baseline][qid])
            arm_mean = sum(task_values[arm][qid]) / len(task_values[arm][qid])
            per_task_deltas.append(arm_mean - base_mean)
        comparisons[arm] = {
            "absolute_delta": arm_means[arm] - arm_means[baseline],
            "relative_delta_percent": (
                None
                if arm_means[baseline] == 0
                else (arm_means[arm] - arm_means[baseline]) / arm_means[baseline] * 100
            ),
            "task_mean_delta": sum(per_task_deltas) / len(per_task_deltas),
            "wins": sum(value > 0 for value in sample_deltas),
            "ties": sum(value == 0 for value in sample_deltas),
            "regressions": sum(value < 0 for value in sample_deltas),
        }
    exclusion_list = sorted(
        exclusions.values(),
        key=lambda item: (item["arm"], item["question_id"], item["sample_index"]),
    )
    warning = manifest.get("hermes_compatibility", {}).get("status") != "verified"
    if exclusion_list:
        status = "VALID_WITH_EXCLUSIONS_AND_HERMES_WARNING" if warning else "VALID_WITH_EXCLUSIONS"
    else:
        status = "VALID_WITH_HERMES_WARNING" if warning else "VALID"
    summary = {
        "status": status,
        "hermes_compatibility": summary_compatibility(manifest),
        "baseline_arm": baseline,
        "arms": arm_names,
        "planned_pairs": len(expected),
        "common_valid_pairs": len(common_valid),
        "paired_coverage_fraction": len(common_valid) / len(expected),
        "planned_cells": len(expected) * len(arm_names),
        "valid_cells": sum(len(values) for values in valid_by_arm.values()),
        "excluded_cells": len(exclusion_list),
        "arm_coverage": {
            arm: {
                "planned_cells": len(expected),
                "valid_cells": len(valid_by_arm[arm]),
                "excluded_cells": len(expected) - len(valid_by_arm[arm]),
            }
            for arm in arm_names
        },
        "exclusions": exclusion_list,
        "arm_means": arm_means,
        "comparisons_vs_baseline": comparisons,
        "category_means": {
            arm: {
                category: sum(values) / len(values)
                for category, values in sorted(categories.items())
            }
            for arm, categories in category_values.items()
        },
        "timing": timing_summary(manifest, records),
        "reference_phase_timing": {
            "status": "unavailable",
            "reason": (
                "Hermes 0.19.1 MoA traces do not persist reference phase timestamps or duration"
            ),
        },
        "scores_sha256": sha256_bytes(canonical_json(scores)),
    }
    (run_dir / "scores.json").write_bytes(canonical_json(scores) + b"\n")
    (run_dir / "paired-deltas.json").write_bytes(canonical_json(cells) + b"\n")
    (run_dir / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return summary
