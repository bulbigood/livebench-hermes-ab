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
    assert "WARNING: fewer than 5 common-valid samples per task" in report
    assert "| 1 | 0 | Unavailable |" in report


def test_historical_zero_exit_provider_failure_is_reclassified_before_scoring() -> None:
    arms = ("base", "candidate")
    outcomes = (
        ValidOutcome(
            CellId("base", "p1", "q", 1),
            {"answer": "API call failed after 3 retries: [Errno 32] Broken pipe"},
            1.0,
        ),
        ValidOutcome(CellId("candidate", "p1", "q", 1), {"answer": "1"}, 1.0),
        ValidOutcome(CellId("base", "p2", "q", 2), {"answer": "1"}, 1.0),
        ValidOutcome(CellId("candidate", "p2", "q", 2), {"answer": "1"}, 1.0),
    )
    run = FrozenRun(
        arms,
        "base",
        ("p1", "p2"),
        outcomes,
        {"q": QuestionEvidence("cat", "task", {})},
        samples_per_task=2,
    )

    result = score_run(run, {"task": lambda _q, answer: float(answer)})

    assert result.common_pairs == ("p2",)
    assert result.exclusion_counts == {"MODEL_OR_PROVIDER_FAILURE": 1}
    assert result.arm_means == {"base": 1.0, "candidate": 1.0}


def test_missing_frozen_scenario_reports_zero_common_coverage() -> None:
    q1 = QuestionEvidence("cat", "task", {"question_id": "q1"})
    q2 = QuestionEvidence("cat", "task", {"question_id": "q2"})
    outcomes = (
        ValidOutcome(CellId("base", "q1", "q1", 0), {"answer": "ok"}, 1.0),
        ValidOutcome(CellId("candidate", "q1", "q1", 0), {"answer": "ok"}, 1.0),
        ExcludedOutcome(
            CellId("base", "q2", "q2", 0), ExclusionCode.MODEL_OR_PROVIDER_FAILURE, "failed", 1.0
        ),
        ExcludedOutcome(
            CellId("candidate", "q2", "q2", 0),
            ExclusionCode.MODEL_OR_PROVIDER_FAILURE,
            "failed",
            1.0,
        ),
    )
    run = FrozenRun(
        ("base", "candidate"),
        "base",
        ("q1", "q2"),
        outcomes,
        {"q1": q1, "q2": q2},
    )
    result = score_run(run, {"task": lambda _question, _answer: 1.0})
    report = render_markdown_report(result)

    assert result.minimum_common_samples_per_task == 0
    assert result.scenario_coverage == {"q1": 1, "q2": 0}
    assert "| cat | task | base | 0 | — | — | — | q2 |" in report


def test_report_pairs_mean_with_median_and_embeds_frozen_config_provenance() -> None:
    outcomes = tuple(
        ValidOutcome(
            CellId(arm, f"q1-s{sample}", "q1", sample),
            {"answer": answer},
            float(sample),
        )
        for sample, answers in ((1, ("0", "1")), (2, ("1", "1")))
        for arm, answer in zip(("base", "candidate"), answers, strict=True)
    )
    result = score_run(
        FrozenRun(
            ("base", "candidate"),
            "base",
            ("q1-s1", "q1-s2"),
            outcomes,
            {"q1": QuestionEvidence("math", "olympiad", {})},
            samples_per_task=2,
        ),
        {"olympiad": lambda _q, answer: float(answer)},
    )
    snapshot = "compatibility:\n  hermes:\n    repository: https://example.test/hermes.git\n    commit: 0123456789012345678901234567890123456789\n"
    report = render_markdown_report(result, snapshot, "Hermes Agent v0.20.1")

    headers = [line for line in report.splitlines() if line.startswith("|") and "---" not in line]
    for header in headers:
        assert ("Mean" in header) == ("Median" in header), header
    assert "| Arm | Mean | Median |" in report
    assert "| Candidate vs baseline | n | Mean delta | Median delta | Harm rate | Catastrophic harm rate | 95% CI |" in report
    assert "Hermes source: `https://example.test/hermes.git @ 0123456789012345678901234567890123456789`" in report
    assert "Observed Hermes: `Hermes Agent v0.20.1`" in report
    assert "<details>" in report
    assert "<summary>Frozen run configuration</summary>" in report
    assert snapshot.rstrip() in report


def test_report_includes_variance_confidence_interval_and_sample_recommendation() -> None:
    arms = ("base", "candidate")
    outcomes = []
    values = {
        "base": (0.0, 0.5, 1.0, 0.5, 1.0),
        "candidate": (0.5, 1.0, 1.0, 0.5, 0.5),
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
    assert "## Sampling" in report
    assert "Sample variance" not in report
    assert "95% CI" in report
    assert "Recommended samples/task" in report
    assert f"| 5 | 5 | {base.recommended_samples_per_task} |" in report
    assert "fewer than 5" not in report

    bundle = scoring_bundle(result, report)
    summary = json.loads(bundle.files[next(p for p in bundle.files if p.name == "summary.json")])
    assert summary["statistical_analysis"]["confidence_level"] == 0.95
    assert summary["statistical_analysis"]["target_margin_of_error"] == 0.05
    assert summary["statistical_analysis"]["arms"]["base"]["sample_variance"] == 0.175
    assert summary["statistical_analysis"]["recommended_samples_per_task"] is not None
    decision = summary["paired_decision_analysis"]["comparisons"]["candidate"]
    assert decision["confidence_level"] == 0.95
    assert decision["power"] == 0.95
    assert decision["verdict"] == "inconclusive"
    assert decision["harm_count"] == 1
    assert decision["harm_rate"] == 0.2
    assert decision["catastrophic_harm_threshold"] == -0.5
    assert decision["catastrophic_harm_count"] == 1
    assert decision["catastrophic_harm_rate"] == 0.2
    assert decision["required_total_pairs_for_projected_ci_excluding_zero"] is not None
    assert decision["required_samples_per_scenario_for_projected_ci_excluding_zero"] is not None
    assert decision["required_total_pairs_for_95_percent_power"] is not None
    assert decision["required_samples_per_scenario_for_95_percent_power"] is not None
    assert "## Paired better/worse decision analysis" in report
    assert "| candidate vs base | 5 | 0.1000 | 0.0000 | 20.0% | 20.0% |" in report
    assert "Catastrophic harm means a paired score delta `<= -0.5`." in report
    assert "95% power samples/scenario" in report


def test_report_and_summary_include_per_scenario_and_family_percentiles() -> None:
    arms = ("base", "candidate")
    outcomes = []
    questions = {
        "q1": QuestionEvidence("math", "olympiad", {}),
        "q2": QuestionEvidence("math", "olympiad", {}),
        "q3": QuestionEvidence("data_analysis", "cta", {}),
    }
    scores = {
        "q1": {"base": (0.0, 1.0), "candidate": (0.5, 1.0)},
        "q2": {"base": (0.2, 0.4), "candidate": (0.3, 0.9)},
        "q3": {"base": (0.0, 0.0), "candidate": (0.0, 0.2)},
    }
    pairs = []
    for question_id, arm_values in scores.items():
        for sample_index in (1, 2):
            pair = f"{question_id}-s{sample_index}"
            pairs.append(pair)
            for arm in arms:
                outcomes.append(
                    ValidOutcome(
                        CellId(arm, pair, question_id, sample_index),
                        {"answer": str(arm_values[arm][sample_index - 1])},
                        1.0,
                    )
                )
    run = FrozenRun(arms, "base", tuple(pairs), tuple(outcomes), questions, samples_per_task=2)
    result = score_run(
        run,
        {task: lambda _q, answer: float(answer) for task in ("olympiad", "cta")},
    )
    report = render_markdown_report(result)
    bundle = scoring_bundle(result, report)
    summary = json.loads(bundle.files[next(p for p in bundle.files if p.name == "summary.json")])

    scenario = summary["grouped_statistics"]["scenarios"]["q1"]
    assert scenario["category"] == "math"
    assert scenario["family"] == "olympiad"
    assert scenario["arms"]["base"] == {
        "n": 2,
        "mean": 0.5,
        "sample_standard_deviation": 2**-0.5,
        "percentiles": {"p05": 0.05, "p25": 0.25, "p50": 0.5, "p75": 0.75, "p95": 0.95},
    }
    assert scenario["paired_deltas_vs_baseline"]["candidate"]["percentiles"]["p50"] == 0.25
    family = summary["grouped_statistics"]["families"]["olympiad"]
    assert family["scenario_count"] == 2
    assert family["arms"]["candidate"]["n"] == 4
    assert family["arms"]["candidate"]["percentiles"]["p95"] == 0.985
    timing = summary["timing_statistics"]
    assert timing["cohort"] == "common_valid_pairs"
    assert timing["overall"]["arms"]["base"]["n"] == 6
    assert timing["overall"]["arms"]["base"]["sum_seconds"] == 6.0
    assert timing["scenarios"]["q1"]["arms"]["candidate"]["mean"] == 1.0
    assert timing["scenarios"]["q1"]["paired_deltas_vs_baseline"]["candidate"]["mean"] == 0.0
    assert timing["families"]["olympiad"]["arms"]["base"]["n"] == 4
    assert "## Score by scenario" in report
    assert "## Paired score deltas by scenario" in report
    assert "## Score by family" in report
    assert "## Paired score deltas by family" in report
    assert "## Overall wall time" in report
    assert "## Wall time by scenario" in report
    assert "## Paired wall-time deltas by scenario" in report
    assert "## Wall time by family" in report
    assert "## Paired wall-time deltas by family" in report
    assert "| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |" in report
    assert "| math | olympiad | base | 2 | 0.5000 | 0.5000 | 0.9500 | q1 |" in report
    assert "| olympiad | 2 | candidate | 4 |" in report
    assert "Arm/paired delta" not in report
    assert "Delta vs baseline" not in report
    assert "| SD |" not in report
    assert "p05" not in report
    assert "p25" not in report
    assert "p75" not in report
    scenario_score = report.index("## Score by scenario")
    scenario_delta = report.index("## Paired score deltas by scenario")
    assert report.index("| math | olympiad | base |", scenario_score, scenario_delta) >= 0
    assert "Δ candidate−base" not in report[scenario_score:scenario_delta]


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


def test_configured_nonbaseline_contrasts_are_scored_and_reported() -> None:
    import pytest

    arms = ("base", "legacy", "critic")
    pairs = tuple(f"p{i}" for i in range(1, 6))
    values = {
        "base": (0.0, 0.0, 0.0, 0.0, 0.0),
        "legacy": (0.1, 0.1, 0.1, 0.1, 0.1),
        "critic": (0.3, 0.3, 0.3, 0.3, 0.3),
    }
    outcomes = tuple(
        ValidOutcome(
            CellId(arm, pair, "q", index),
            {"answer": str(values[arm][index - 1])},
            1.0,
        )
        for index, pair in enumerate(pairs, 1)
        for arm in arms
    )
    run = FrozenRun(
        arms,
        "base",
        pairs,
        outcomes,
        {"q": QuestionEvidence("math", "task", {})},
        samples_per_task=5,
        contrasts=(("critic", "legacy"), ("critic", "base")),
    )
    result = score_run(run, {"task": lambda _q, answer: float(answer)})
    report = render_markdown_report(result)
    bundle = scoring_bundle(result, report)
    summary = json.loads(bundle.files[next(p for p in bundle.files if p.name == "summary.json")])

    contrast = summary["planned_contrast_analysis"]["comparisons"]["critic_vs_legacy"]
    assert contrast["left_arm"] == "critic"
    assert contrast["right_arm"] == "legacy"
    assert contrast["observed_mean_delta"] == pytest.approx(0.2)
    assert contrast["verdict"] == "better"
    assert "## Planned paired contrasts" in report
    assert "| critic vs legacy |" in report
