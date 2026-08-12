from __future__ import annotations

import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

from .domain import IntegrityError


def _enable_pinned_livebench() -> None:
    upstream = Path(__file__).resolve().parents[2] / "upstream"
    if str(upstream) not in sys.path:
        sys.path.insert(0, str(upstream))


def objective_score(question: Mapping[str, object], answer: str) -> float:
    _enable_pinned_livebench()
    task = str(question["task"])
    truth = question.get("ground_truth")
    if task == "spatial":
        from livebench.process_results.reasoning.spatial.utils import spatial_process_results

        return float(spatial_process_results(truth, answer, debug=False))
    if task == "zebra_puzzle":
        from livebench.process_results.reasoning.zebra_puzzle.utils import (
            get_zebra_puzzle_evaluator,
        )

        return float(
            get_zebra_puzzle_evaluator(str(question["livebench_release_date"]))(truth, answer)
        )
    if task == "tablejoin":
        from livebench.process_results.data_analysis.tablejoin.utils import joinmap_process_results

        return float(joinmap_process_results(str(question["turns"][0]), truth, answer, debug=False))  # type: ignore[index]
    if task == "tablereformat":
        from livebench.process_results.data_analysis.tablereformat.utils import (
            table_process_results,
        )

        version = "v2" if str(question["livebench_release_date"]) >= "2025-04-25" else "v1"
        return float(
            table_process_results(str(question["turns"][0]), truth, answer, version, debug=False)
        )  # type: ignore[index]
    if task == "exact_match":
        return float(answer.strip() == str(truth).strip())
    raise IntegrityError(f"unsupported objective scoring task: {task}")


def instruction_score(question: Mapping[str, object], answer: str) -> float:
    _enable_pinned_livebench()
    import nltk
    from livebench.if_runner.instruction_following_eval import evaluation_main

    cache = Path.home() / ".cache" / "nltk_data"
    if str(cache) not in nltk.data.path:
        nltk.data.path.insert(0, str(cache))
    for resource in ("tokenizers/punkt", "tokenizers/punkt_tab/english"):
        try:
            nltk.data.find(resource)
        except LookupError as exc:
            raise IntegrityError(f"missing deterministic NLTK resource: {resource}") from exc
    qid = str(question["question_id"])
    record = {"question_id": qid, "choices": [{"index": 0, "turns": [answer]}]}
    with tempfile.TemporaryDirectory(prefix="livebench-if-") as directory:
        values = evaluation_main.evaluator(
            [dict(question)], {"candidate": {qid: record}}, directory, "candidate"
        )["strict"]
    if len(values) != 1 or not values[0].follow_instruction_list:
        raise IntegrityError("instruction evaluator returned incomplete results")
    item = values[0]
    per_instruction = [1 if status else 0 for status in item.follow_instruction_list]
    return (
        (1 if item.follow_all_instructions else 0) + sum(per_instruction) / len(per_instruction)
    ) / 2


def registry(tasks: set[str]):
    instruction_tasks = {"summarize", "simplify", "paraphrase", "story_generation"}
    return {
        task: instruction_score if task in instruction_tasks else objective_score for task in tasks
    }
