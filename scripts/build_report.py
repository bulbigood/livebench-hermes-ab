from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import statistics
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def build(run: Path, output_root: Path, seed: int = 5601) -> dict[str, Any]:
    scores = json.loads((run / "scores.json").read_text(encoding="utf-8"))
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in scores:
        grouped.setdefault(row["question_id"], {})[row["arm"]] = row
    pairs = []
    for qid, arms in grouped.items():
        base = float(arms["base"]["score"])
        moa = float(arms["moa"]["score"])
        pairs.append(
            {
                "question_id": qid,
                "category": arms["base"]["category"],
                "task": arms["base"]["task"],
                "base": base,
                "moa": moa,
                "delta": moa - base,
            }
        )
    deltas = [pair["delta"] for pair in pairs]
    rng = random.Random(seed)
    bootstrap = sorted(
        sum(rng.choice(deltas) for _ in deltas) / len(deltas) for _ in range(10_000)
    )
    base_rows = load_jsonl(run / "raw/hermes-base.jsonl")
    moa_rows = load_jsonl(run / "raw/hermes-moa.jsonl")
    base_wall = sum(float(row["total_time_s"]) for row in base_rows)
    moa_wall = sum(float(row["total_time_s"]) for row in moa_rows)
    trace_audit = json.loads((run / "trace-audit.json").read_text(encoding="utf-8"))

    usage: dict[str, Any] = {}
    for arm in ("base", "moa"):
        con = sqlite3.connect(run / f"homes/{arm}/state.db")
        rows = con.execute(
            "SELECT api_call_count,input_tokens,output_tokens,cache_read_tokens,"
            "reasoning_tokens FROM session_model_usage"
        ).fetchall()
        zero_sessions = con.execute(
            "SELECT COUNT(*) FROM sessions WHERE COALESCE(input_tokens,0)=0 "
            "AND COALESCE(output_tokens,0)=0"
        ).fetchone()[0]
        usage[arm] = {
            "usage_rows": len(rows),
            "api_calls_recorded": sum(int(row[0] or 0) for row in rows),
            "input_tokens_recorded": sum(int(row[1] or 0) for row in rows),
            "output_tokens_recorded": sum(int(row[2] or 0) for row in rows),
            "cache_read_tokens_recorded": sum(int(row[3] or 0) for row in rows),
            "reasoning_tokens_recorded": sum(int(row[4] or 0) for row in rows),
            "zero_usage_sessions": zero_sessions,
            "complete": zero_sessions == 0,
        }

    report = {
        "verdict": "PROMISING_NOT_CONCLUSIVE",
        "technical_validity": "VALID_WITH_BASE_TOKEN_TELEMETRY_LIMITATION",
        "pairs": pairs,
        "summary": {
            "pair_count": len(pairs),
            "base_mean": statistics.mean(pair["base"] for pair in pairs),
            "moa_mean": statistics.mean(pair["moa"] for pair in pairs),
            "mean_delta": statistics.mean(deltas),
            "median_delta": statistics.median(deltas),
            "bootstrap_95pct_mean_delta": [
                bootstrap[int(0.025 * len(bootstrap))],
                bootstrap[int(0.975 * len(bootstrap)) - 1],
            ],
            "improved": sum(delta > 0 for delta in deltas),
            "tied": sum(delta == 0 for delta in deltas),
            "regressed": sum(delta < 0 for delta in deltas),
        },
        "latency": {
            "base_wall_s": base_wall,
            "moa_wall_s": moa_wall,
            "overhead_s": moa_wall - base_wall,
            "overhead_pct": (moa_wall / base_wall - 1) * 100,
        },
        "trace_audit": trace_audit,
        "usage": usage,
        "cost": {
            "usd_total": None,
            "reason": "Reference costs are provider estimates serialized as strings; BASE OpenAI Codex is included. No verified comparable USD total.",
        },
        "provisional_run_excluded": "runs/smoke-provisional-untraced",
        "artifact_sha256": {
            "manifest": sha256(run / "manifest.json"),
            "questions": sha256(run / "questions.json"),
            "base_answers": sha256(run / "raw/hermes-base.jsonl"),
            "moa_answers": sha256(run / "raw/hermes-moa.jsonl"),
            "scores": sha256(run / "scores.json"),
            "trace_audit": sha256(run / "trace-audit.json"),
        },
        "limitations": [
            "Only five heterogeneous tasks; this is a demanding smoke test, not a stable population estimate.",
            "Two BASE sessions did not persist token usage; latency and scores are complete, BASE token totals are not.",
            "The bootstrap interval includes zero and is descriptive for the frozen five-task sample only.",
        ],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "smoke-traced.json"
    md_path = output_root / "smoke-traced.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    s = report["summary"]
    l = report["latency"]
    lines = [
        "# LiveBench Hermes BASE vs MoA — traced smoke",
        "",
        f"**Verdict:** `{report['verdict']}`",
        f"**Technical validity:** `{report['technical_validity']}`",
        "",
        "## Result",
        "",
        f"- Pairs: {s['pair_count']}",
        f"- BASE mean: {s['base_mean']:.4f}",
        f"- MoA mean: {s['moa_mean']:.4f}",
        f"- Mean paired delta: {s['mean_delta']:+.4f}",
        f"- Median paired delta: {s['median_delta']:+.4f}",
        f"- Bootstrap 95% interval: [{s['bootstrap_95pct_mean_delta'][0]:.4f}, {s['bootstrap_95pct_mean_delta'][1]:.4f}]",
        f"- Improved / tied / regressed: {s['improved']} / {s['tied']} / {s['regressed']}",
        "",
        "## Latency",
        "",
        f"- BASE: {l['base_wall_s']:.1f}s",
        f"- MoA: {l['moa_wall_s']:.1f}s",
        f"- Overhead: {l['overhead_s']:+.1f}s ({l['overhead_pct']:+.1f}%)",
        "",
        "## Integrity",
        "",
        f"- MoA traces: {trace_audit['trace_records']}/5",
        f"- Valid Minimax references: {trace_audit['reference_calls']}/5",
        f"- Reference tokens: {trace_audit['reference_input_tokens']} input, {trace_audit['reference_output_tokens']} output",
        f"- Aggregator outputs match answer artifacts: {trace_audit['answer_trace_hashes_match']}",
        "- Tools: zero schemas in both arms",
        "- Scoring: pinned objective LiveBench task processors",
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
        "The earlier untraced run is preserved but excluded from the headline because it could not prove reference cardinality.",
    ]
    md_path.write_text("\n".join(lines) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("runs/smoke"))
    parser.add_argument("--output", type=Path, default=Path("reports"))
    args = parser.parse_args()
    print(json.dumps(build(args.run, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
