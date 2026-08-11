from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from livebench_hermes_ab.scoring import answer_text, score_instruction_following, score_standard

ROOT = Path(__file__).resolve().parents[1]
AB = ROOT / "runs/medium-10new-5samples-v1"
C_RUN = ROOT / "runs/moa-low-10new-5samples-v1"
OUT_JSON = ROOT / "reports/abc-medium-base-moa-medium-moa-low.json"
OUT_MD = ROOT / "reports/abc-medium-base-moa-medium-moa-low.md"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def cell(row):
    return str(row["question_id"]), int(row.get("sample_index", 0))


def summarize_pair(left, right, cells, questions):
    deltas = {c: right[c] - left[c] for c in cells}
    by_task = defaultdict(list)
    for c, delta in deltas.items():
        by_task[c[0]].append(delta)
    task_means = {qid: statistics.mean(values) for qid, values in by_task.items()}
    values = list(deltas.values())
    task_values = list(task_means.values())
    rng = random.Random(5601)
    boots = [statistics.mean(rng.choices(task_values, k=len(task_values))) for _ in range(100000)]
    boots.sort()
    return {
        "n": len(cells),
        "left_mean": statistics.mean(left[c] for c in cells),
        "right_mean": statistics.mean(right[c] for c in cells),
        "sample_mean_delta": statistics.mean(values),
        "equal_task_mean_delta": statistics.mean(task_values),
        "task_cluster_bootstrap_95pct": [boots[2500], boots[97499]],
        "sample_wins_ties_regressions": {
            "wins": sum(x > 0 for x in values),
            "ties": sum(x == 0 for x in values),
            "regressions": sum(x < 0 for x in values),
        },
        "task_wins_ties_regressions": {
            "wins": sum(x > 0 for x in task_values),
            "ties": sum(x == 0 for x in task_values),
            "regressions": sum(x < 0 for x in task_values),
        },
        "task_mean_deltas": {
            f"{questions[qid]['category']}/{questions[qid]['task']}/{qid[:12]}": value
            for qid, value in sorted(task_means.items())
        },
    }


def latency(rows, cells):
    selected = [float(row["total_time_s"]) for row in rows if cell(row) in cells]
    return {
        "total_s": sum(selected),
        "mean_s": statistics.mean(selected),
        "median_s": statistics.median(selected),
    }


def main():
    questions = {str(q["question_id"]): q for q in load_json(AB / "questions.json")}
    ab_scores = load_json(AB / "scores.json")
    scores = {
        "A_base_medium": {},
        "B_moa_medium": {},
        "C_moa_low": {},
    }
    for row in ab_scores:
        key = (str(row["question_id"]), int(row["sample_index"]))
        target = "A_base_medium" if row["arm"] == "base" else "B_moa_medium"
        scores[target][key] = float(row["score"])

    c_rows = load_rows(C_RUN / "raw/hermes-moa.jsonl")
    c_score_rows = []
    for row in c_rows:
        key = cell(row)
        question = questions[key[0]]
        if question["category"] == "instruction_following":
            value = score_instruction_following(
                question, row, "moa-low", C_RUN / "if-evaluator/moa-low" / str(key[1])
            )
        else:
            value = score_standard(question, answer_text(row))
        scores["C_moa_low"][key] = value
        c_score_rows.append({"question_id": key[0], "sample_index": key[1], "score": value})
    (C_RUN / "scores-moa-low.json").write_text(json.dumps(c_score_rows, sort_keys=True) + "\n")

    common = set.intersection(*(set(v) for v in scores.values()))
    comparisons = {
        "A_to_B": summarize_pair(
            scores["A_base_medium"], scores["B_moa_medium"], common, questions
        ),
        "A_to_C": summarize_pair(scores["A_base_medium"], scores["C_moa_low"], common, questions),
        "C_to_B": summarize_pair(scores["C_moa_low"], scores["B_moa_medium"], common, questions),
    }
    a_rows = load_rows(AB / "raw/hermes-base.jsonl")
    b_rows = load_rows(AB / "raw/hermes-moa.jsonl")
    trace_b = load_json(AB / "trace-audit.json")
    trace_c = load_json(C_RUN / "trace-audit.json")
    report = {
        "status": "VALID_ABC_ON_49_COMMON_CELLS",
        "arms": {
            "A": "BASE, openai-codex:gpt-5.6-sol medium",
            "B": "MoA, aggregator openai-codex:gpt-5.6-sol medium, Minimax M3 reference",
            "C": "MoA, aggregator openai-codex:gpt-5.6-sol low, Minimax M3 reference",
        },
        "common_cells": len(common),
        "c_complete_cells": len(scores["C_moa_low"]),
        "comparisons": comparisons,
        "latency_common_cells": {
            "A": latency(a_rows, common),
            "B": latency(b_rows, common),
            "C": latency(c_rows, common),
        },
        "reference_telemetry": {"B": trace_b, "C": trace_c},
        "limitations": [
            "ABC headline uses the 49 cells common to all arms; C has one additional valid cell excluded from pairwise comparisons.",
            "The A/B infrastructure exclusion was authorized after its timeout, so status is not a pristine 50-cell confirmatory design.",
            "Task-cluster intervals are descriptive with only ten heterogeneous tasks.",
            "Main-model token telemetry is incomplete; no USD comparison is inferred.",
        ],
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    def line(name, comparison):
        d = comparison
        ci = d["task_cluster_bootstrap_95pct"]
        wtr = d["sample_wins_ties_regressions"]
        return (
            f"| {name} | {d['left_mean']:.4f} | {d['right_mean']:.4f} | "
            f"{d['sample_mean_delta']:+.4f} | {d['equal_task_mean_delta']:+.4f} | "
            f"[{ci[0]:+.4f}, {ci[1]:+.4f}] | {wtr['wins']}/{wtr['ties']}/{wtr['regressions']} |"
        )

    lat = report["latency_common_cells"]
    md = [
        "# LiveBench ABC — BASE medium vs MoA medium vs MoA low",
        "",
        "**Status:** `VALID_ABC_ON_49_COMMON_CELLS`",
        "",
        "## Headline",
        "",
        "| Comparison | Left | Right | Sample delta | Task delta | Task-cluster 95% | W/T/R |",
        "|---|---:|---:|---:|---:|---:|---:|",
        line("A → B", comparisons["A_to_B"]),
        line("A → C", comparisons["A_to_C"]),
        line("C → B", comparisons["C_to_B"]),
        "",
        "## Latency on 49 common cells",
        "",
        f"- A BASE medium: mean {lat['A']['mean_s']:.1f}s, total {lat['A']['total_s']:.1f}s",
        f"- B MoA medium: mean {lat['B']['mean_s']:.1f}s, total {lat['B']['total_s']:.1f}s",
        f"- C MoA low: mean {lat['C']['mean_s']:.1f}s, total {lat['C']['total_s']:.1f}s",
        "",
        "## Per-task B minus C deltas",
        "",
    ]
    for task, delta in comparisons["C_to_B"]["task_mean_deltas"].items():
        md.append(f"- `{task}`: {delta:+.4f}")
    md += [
        "",
        "## Interpretation",
        "",
        (
            "B versus C isolates aggregator reasoning effort while preserving MoA references. "
            "A versus either MoA arm is a compound comparison against BASE."
        ),
        "",
        "C has 50 valid outputs, but the headline intersection is 49 because A/B lacks one zebra sample.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(
        json.dumps(
            {"json": str(OUT_JSON), "md": str(OUT_MD), "comparisons": comparisons, "latency": lat},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
