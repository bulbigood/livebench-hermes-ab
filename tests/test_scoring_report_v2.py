from livebench_hermes_ab.domain import CellId, ExcludedOutcome, ExclusionCode, ValidOutcome
from livebench_hermes_ab.report import render_markdown_report
from livebench_hermes_ab.scoring import FrozenRun, QuestionEvidence, score_run, scoring_bundle


def test_common_cohort_intersects_every_arm_and_report_preserves_order() -> None:
    arms = ("base", "gpt_medium", "moa_minimax", "moa_mimo")
    outcomes = []
    for qid in ("q1", "q2"):
        for arm in arms:
            cell = CellId(arm, qid, qid, 0)
            if qid == "q2" and arm == "moa_mimo":
                outcomes.append(ExcludedOutcome(cell, ExclusionCode.INVALID_MOA_TRACE, "bad", None))
            else:
                outcomes.append(ValidOutcome(cell, {"answer": f"{arm}-{qid}"}, 1.0))
    run = FrozenRun(
        arms,
        "base",
        ("q1", "q2"),
        tuple(outcomes),
        {"q1": QuestionEvidence("cat", "task", {}), "q2": QuestionEvidence("cat", "task", {})},
    )
    result = score_run(run, {"task": lambda _q, answer: 1.0 if answer.startswith("base") else 2.0})
    assert result.common_pairs == ("q1",)
    assert result.arm_order == arms
    report = render_markdown_report(result)
    assert [report.index(f"| {arm} |") for arm in arms] == sorted(
        report.index(f"| {arm} |") for arm in arms
    )
    bundle = scoring_bundle(result, report)
    assert {path.name for path in bundle.files} == {"summary.json", "scores.json", "report.md"}
    summary = __import__("json").loads(
        bundle.files[next(p for p in bundle.files if p.name == "summary.json")]
    )
    assert summary["trace_audit"]["valid_traces"] == 0


def test_scoring_revalidates_persisted_trace_evidence() -> None:
    import json

    arm = "moa"
    cell = CellId(arm, "p", "q", 0)
    trace = {
        "preset": "p",
        "references": [
            {
                "provider": "openrouter",
                "model": "reference",
                "output": "reference answer",
                "usage": {"input_tokens": 2, "output_tokens": 3},
            }
        ],
        "aggregator": {"provider": "openai", "model": "aggregator", "output": "final"},
    }
    audit = {
        "trace": json.dumps(trace),
        "answer": "final",
        "expected": {
            "preset": "p",
            "references": [["openrouter", "reference"]],
            "aggregator": ["openai", "aggregator"],
        },
    }
    run = FrozenRun(
        (arm,),
        arm,
        ("p",),
        (ValidOutcome(cell, {"answer": "final", "trace_audit": [audit]}, 1.0),),
        {"q": QuestionEvidence("cat", "task", {})},
    )
    result = score_run(run, {"task": lambda _q, _answer: 1.0})
    assert result.trace_audit["valid_traces"] == 1

    trace["aggregator"]["output"] = "tampered"
    audit["trace"] = json.dumps(trace)
    tampered = FrozenRun(
        (arm,),
        arm,
        ("p",),
        (ValidOutcome(cell, {"answer": "final", "trace_audit": [audit]}, 1.0),),
        {"q": QuestionEvidence("cat", "task", {})},
    )
    import pytest

    with pytest.raises(Exception, match="failed revalidation"):
        score_run(tampered, {"task": lambda _q, _answer: 1.0})
