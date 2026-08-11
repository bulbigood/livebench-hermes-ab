from __future__ import annotations

import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/medium-10new-5samples-v1"
REPORT_JSON = ROOT / "reports/medium-10new-5samples.json"
REPORT_MD = ROOT / "reports/medium-10new-5samples.md"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    questions = {q["question_id"]: q for q in read_json(RUN / "questions.json")}
    deltas = read_json(RUN / "paired-deltas.json")
    summary = read_json(RUN / "summary.json")
    audit = read_json(RUN / "trace-audit.json")
    amendment = read_json(RUN / "run-amendment.json")
    answers = {}
    for arm in ("base", "moa"):
        answers[arm] = [json.loads(line) for line in (RUN / "raw" / f"hermes-{arm}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    grouped = defaultdict(list)
    for row in deltas:
        grouped[row["question_id"]].append(row)
    tasks = []
    for qid, rows in sorted(grouped.items()):
        q = questions[qid]
        vals = [r["delta"] for r in rows]
        base = [r["base"] for r in rows]
        moa = [r["moa"] for r in rows]
        tasks.append({
            "question_id": qid,
            "category": q["category"],
            "task": q["task"],
            "samples": len(rows),
            "base_mean": statistics.mean(base),
            "moa_mean": statistics.mean(moa),
            "mean_delta": statistics.mean(vals),
            "delta_stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "wins": sum(v > 0 for v in vals),
            "ties": sum(v == 0 for v in vals),
            "regressions": sum(v < 0 for v in vals),
        })

    task_deltas = [t["mean_delta"] for t in tasks]
    rng = random.Random(5601)
    boots = sorted(statistics.mean(rng.choices(task_deltas, k=len(task_deltas))) for _ in range(100_000))
    ci = [boots[2500], boots[97499]]
    latency = {}
    for arm in ("base", "moa"):
        vals = [float(r["total_time_s"]) for r in answers[arm]]
        latency[arm] = {"total_s": sum(vals), "mean_s": statistics.mean(vals), "median_s": statistics.median(vals)}
    latency["paired_overhead"] = {
        "total_s": latency["moa"]["total_s"] - latency["base"]["total_s"],
        "percent": (latency["moa"]["total_s"] / latency["base"]["total_s"] - 1) * 100,
    }

    result = {
        "status": summary["status"],
        "verdict": "PROMISING_NOT_GENERAL",
        "design": {"tasks": 10, "planned_samples_per_task": 5, "scored_pairs": 49, "excluded_pairs": 1, "reasoning": "medium"},
        "scores": summary,
        "task_cluster_bootstrap_95pct": ci,
        "tasks": tasks,
        "latency": latency,
        "references": audit,
        "exclusion": amendment,
        "telemetry": {"reference_usage_complete": True, "main_usage_complete": False, "usd_cost_reported": False},
        "artifacts": {name: sha256(RUN / name) for name in ["manifest.json", "questions.json", "scores.json", "paired-deltas.json", "trace-audit.json", "run-amendment.json"]},
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# LiveBench Hermes BASE vs MoA — medium, 10 new tasks × 5 samples",
        "",
        f"**Status:** `{result['status']}`  ",
        f"**Verdict:** `{result['verdict']}`",
        "",
        "## Headline",
        "",
        f"- Scored pairs: {summary['scored_pairs']}/{summary['planned_pairs']} (one infrastructure timeout excluded by operator authorization).",
        f"- BASE mean: {summary['base_mean']:.4f}",
        f"- MoA mean: {summary['moa_mean']:.4f}",
        f"- Sample-weighted delta: {summary['sample_mean_delta']:+.4f}",
        f"- Equal-task-weighted delta: {summary['task_mean_delta']:+.4f}",
        f"- Task-cluster bootstrap 95% interval: [{ci[0]:+.4f}, {ci[1]:+.4f}]",
        f"- Sample wins/ties/regressions: {summary['sample_wins_ties_regressions']['wins']}/{summary['sample_wins_ties_regressions']['ties']}/{summary['sample_wins_ties_regressions']['regressions']}",
        f"- Task wins/ties/regressions: {summary['task_wins_ties_regressions']['wins']}/{summary['task_wins_ties_regressions']['ties']}/{summary['task_wins_ties_regressions']['regressions']}",
        "",
        "## Per task",
        "",
        "| Category | Task | n | BASE | MoA | Delta | SD(delta) | W/T/R |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for t in tasks:
        lines.append(f"| {t['category']} | {t['task']} | {t['samples']} | {t['base_mean']:.4f} | {t['moa_mean']:.4f} | {t['mean_delta']:+.4f} | {t['delta_stdev']:.4f} | {t['wins']}/{t['ties']}/{t['regressions']} |")
    lines += [
        "",
        "## Latency and telemetry",
        "",
        f"- BASE total wall time: {latency['base']['total_s']:.1f}s",
        f"- MoA total wall time: {latency['moa']['total_s']:.1f}s",
        f"- MoA overhead: {latency['paired_overhead']['total_s']:+.1f}s ({latency['paired_overhead']['percent']:+.1f}%)",
        f"- Valid Minimax references: {audit['reference_calls']}/49",
        f"- Minimax usage: {audit['reference_input_tokens']} input / {audit['reference_output_tokens']} output tokens",
        "- Main-model token telemetry is incomplete; no USD cost is inferred.",
        "",
        "## Interpretation",
        "",
        "MoA improved six samples and regressed none, but only two of ten tasks improved. Most lift came from one zebra-puzzle task; eight tasks tied. The interval touches zero under task-cluster resampling. This supports targeted use for difficult symbolic reasoning, not general adoption.",
        "",
        "The excluded zebra sample timed out before either arm answer was persisted. The remaining four zebra samples are paired and included. No model output was rerun or selected by score.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(REPORT_JSON), "markdown": str(REPORT_MD), "ci": ci, "latency": latency}, indent=2))


if __name__ == "__main__":
    main()
