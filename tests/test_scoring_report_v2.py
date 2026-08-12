import json

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
    assert summary["samples_per_task"] == 1
    assert summary["statistical_analysis"]["sufficient_pilot_samples"] is False
    assert summary["statistical_analysis"]["arms"]["base"]["sample_variance"] is None
    assert "WARNING: minimum common-valid samples per task is 1; fewer than 5" in report
    assert "Recommended samples/task | Unavailable" in report


def test_report_includes_variance_confidence_interval_and_sample_recommendation() -> None:
    arms = ("base", "candidate")
    outcomes = []
    values = {
        "base": (0.0, 0.5, 1.0, 0.5, 1.0),
        "candidate": (0.5, 1.0, 1.0, 0.5, 0.0),
    }
    for sample_index in range(1, 6):
        pair = f"q1-s{sample_index}"
        for arm in arms:
            outcomes.append(
                ValidOutcome(
                    CellId(arm, pair, "q1", sample_index),
                    {"answer": str(values[arm][sample_index - 1])},
                    1.0,
                )
            )
    run = FrozenRun(
        arms,
        "base",
        tuple(f"q1-s{i}" for i in range(1, 6)),
        tuple(outcomes),
        {"q1": QuestionEvidence("cat", "task", {})},
        samples_per_task=5,
    )
    result = score_run(run, {"task": lambda _q, answer: float(answer)})
    base = result.arm_statistics["base"]
    assert base.observations == 5
    assert base.sample_variance == 0.175
    assert base.standard_deviation is not None
    assert base.standard_error is not None
    assert base.confidence_interval is not None
    assert base.recommended_samples_per_task is not None
    assert base.recommended_samples_per_task >= 5

    report = render_markdown_report(result)
    assert "## Statistical analysis" in report
    assert "Sample variance" in report
    assert "95% CI" in report
    assert "Recommended samples/task" in report
    assert "Overall recommended samples/task:" in report
    assert "fewer than 5" not in report

    bundle = scoring_bundle(result, report)
    summary = json.loads(bundle.files[next(p for p in bundle.files if p.name == "summary.json")])
    assert summary["statistical_analysis"]["confidence_level"] == 0.95
    assert summary["statistical_analysis"]["target_margin_of_error"] == 0.05
    assert summary["statistical_analysis"]["arms"]["base"]["sample_variance"] == 0.175
    assert summary["statistical_analysis"]["recommended_samples_per_task"] is not None


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
