from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .core import ContractError, canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "upstream"
if str(UPSTREAM) not in sys.path:
    sys.path.insert(0, str(UPSTREAM))


def _load_answers(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise ContractError(f"missing answer file: {path}")
    rows: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            qid = str(row["question_id"])
            if qid in rows:
                raise ContractError(f"duplicate answer for {qid} in {path}")
            rows[qid] = row
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
    raise ContractError(f"unsupported smoke scoring task: {task}")


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
                "missing NLTK scoring data; install punkt and punkt_tab in "
                f"{nltk_cache}"
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
    return ((1 if item.follow_all_instructions else 0) + sum(per_instruction) / len(per_instruction)) / 2


def score_run(run_dir: Path) -> dict[str, Any]:
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    expected = {str(question["question_id"]) for question in questions}
    records = {
        arm: _load_answers(run_dir / "raw" / f"hermes-{arm}.jsonl")
        for arm in ("base", "moa")
    }
    for arm, rows in records.items():
        if set(rows) != expected:
            raise ContractError(f"{arm} answer coverage mismatch")

    scores: list[dict[str, Any]] = []
    by_category: dict[str, list[float]] = defaultdict(list)
    for question in questions:
        qid = str(question["question_id"])
        pair_scores: dict[str, float] = {}
        for arm in ("base", "moa"):
            record = records[arm][qid]
            if question["category"] == "instruction_following":
                score = score_instruction_following(
                    question, record, arm, run_dir / "if-evaluator" / arm
                )
            else:
                score = score_standard(question, answer_text(record))
            pair_scores[arm] = score
            scores.append(
                {
                    "question_id": qid,
                    "category": question["category"],
                    "task": question["task"],
                    "arm": arm,
                    "score": score,
                }
            )
        by_category[str(question["category"])].append(pair_scores["moa"] - pair_scores["base"])

    base_scores = [row["score"] for row in scores if row["arm"] == "base"]
    moa_scores = [row["score"] for row in scores if row["arm"] == "moa"]
    summary = {
        "pairs": len(questions),
        "base_mean": sum(base_scores) / len(base_scores),
        "moa_mean": sum(moa_scores) / len(moa_scores),
        "mean_delta": sum(moa_scores) / len(moa_scores) - sum(base_scores) / len(base_scores),
        "category_mean_delta": {
            category: sum(values) / len(values) for category, values in sorted(by_category.items())
        },
        "scores_sha256": sha256_bytes(canonical_json(scores)),
    }
    (run_dir / "scores.json").write_bytes(canonical_json(scores) + b"\n")
    (run_dir / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return summary
