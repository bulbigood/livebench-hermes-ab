from __future__ import annotations

import statistics

import yaml

from .scoring import (
    ScoringResult,
    grouped_statistics,
    paired_decision_analysis,
    timing_statistics,
)


def _hermes_source(config_snapshot: str) -> str:
    root = yaml.safe_load(config_snapshot)
    if not isinstance(root, dict):
        raise TypeError("frozen config must be a mapping")
    compatibility = root.get("compatibility")
    if not isinstance(compatibility, dict) or not isinstance(compatibility.get("hermes"), dict):
        raise TypeError("frozen config is missing compatibility.hermes")
    hermes = compatibility["hermes"]
    if "repository" in hermes and "commit" in hermes:
        return f"{hermes['repository']} @ {hermes['commit']}"
    if "directory" in hermes:
        return str(hermes["directory"])
    release = hermes.get("release", hermes.get("profile"))
    if release is None:
        raise ValueError("frozen config has no supported Hermes source")
    return f"release {release} (source commit not recorded)"


def _provenance(config_snapshot: str | None, observed_hermes: str | None) -> list[str]:
    if config_snapshot is None:
        return []
    lines = [
        "",
        "## Run provenance",
        "",
        f"Hermes source: `{_hermes_source(config_snapshot)}`",
    ]
    if observed_hermes is not None:
        lines.append(f"Observed Hermes: `{observed_hermes}`")
    lines.extend(
        [
            "",
            "<details>",
            "<summary>Frozen run configuration</summary>",
            "",
            "```yaml",
            config_snapshot.rstrip(),
            "```",
            "",
            "</details>",
        ]
    )
    return lines


def _arm_median(result: ScoringResult, arm: str) -> float:
    return float(statistics.median(row.score for row in result.rows if row.arm == arm))


def _paired_score_deltas(result: ScoringResult, arm: str) -> list[float]:
    scores = {(row.pair_id, row.arm): row.score for row in result.rows}
    return [
        scores[(pair, arm)] - scores[(pair, result.baseline_arm)]
        for pair in result.common_pairs
    ]


def _statistical_analysis(result: ScoringResult) -> list[str]:
    recommendations = [
        item.recommended_samples_per_task
        for item in result.arm_statistics.values()
        if item.recommended_samples_per_task is not None
    ]
    recommended = "Unavailable" if not recommendations else str(max(recommendations))
    lines = [
        "",
        "## Sampling",
        "",
        "| Configured samples/task | Minimum common-valid samples/task | Recommended samples/task |",
        "|---:|---:|---:|",
        f"| {result.samples_per_task} | {result.minimum_common_samples_per_task} | {recommended} |",
    ]
    if result.minimum_common_samples_per_task < 5:
        lines.extend(
            [
                "",
                (
                    "> WARNING: fewer than 5 common-valid samples per task; "
                    "variance-based planning estimates are unstable."
                ),
            ]
        )
    return lines


def _paired_decision_analysis(result: ScoringResult) -> list[str]:
    analysis = paired_decision_analysis(result)
    comparisons = analysis["comparisons"]
    assert isinstance(comparisons, dict)
    lines = [
        "",
        "## Paired better/worse decision analysis",
        "",
        "The verdict uses a two-sided 95% confidence interval for common-valid paired score differences. Sample projections assume the observed effect and paired-difference variance persist; they are planning estimates, not guarantees.",
        "",
        "| Candidate vs baseline | n | Mean delta | Median delta | 95% CI | Verdict | Projected CI-excluding-zero samples/scenario | 95% power samples/scenario |",
        "|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for arm, item in comparisons.items():
        assert isinstance(item, dict)
        interval = item["confidence_interval"]
        rendered_interval = (
            "Unavailable" if interval is None
            else f"[{float(interval[0]):.4f}, {float(interval[1]):.4f}]"
        )
        projected = item["required_samples_per_scenario_for_projected_ci_excluding_zero"]
        powered = item["required_samples_per_scenario_for_95_percent_power"]
        median_delta = statistics.median(_paired_score_deltas(result, arm))
        lines.append(
            f"| {arm} vs {result.baseline_arm} | {item['observations']} | "
            f"{float(item['observed_mean_delta']):.4f} | {median_delta:.4f} | "
            f"{rendered_interval} | {item['verdict']} | "
            f"{'Unavailable' if projected is None else projected} | "
            f"{'Unavailable' if powered is None else powered} |"
        )
    return lines


def _trace_audit(result: ScoringResult) -> list[str]:
    return [
        "",
        "## Trace audit",
        "",
        f"- Valid traces: {result.trace_audit['valid_traces']}",
        f"- Invalid traces: {result.trace_audit['invalid_traces']}",
        f"- Reference calls: {result.trace_audit['reference_calls']}",
        f"- Reference input tokens: {result.trace_audit['reference_input_tokens']}",
        f"- Reference output tokens: {result.trace_audit['reference_output_tokens']}",
    ]


def _distribution_cells(value: dict[str, object]) -> str:
    percentiles = value["percentiles"]
    assert isinstance(percentiles, dict)
    return " | ".join(
        (
            str(value["n"]),
            f"{float(value['mean']):.4f}",
            f"{float(percentiles['p50']):.4f}",
            f"{float(percentiles['p95']):.4f}",
        )
    )


def _grouped_statistics(result: ScoringResult) -> list[str]:
    grouped = grouped_statistics(result)
    scenarios, families = grouped["scenarios"], grouped["families"]
    assert isinstance(scenarios, dict) and isinstance(families, dict)
    lines = [
        "",
        "## Score by scenario",
        "",
        "| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for question_id, item in scenarios.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(
                f"| {item['category']} | {item['family']} | {arm} | "
                f"{_distribution_cells(item['arms'][arm])} | {question_id} |"
            )
    lines.extend(
        [
            "",
            "## Paired score deltas by scenario",
            "",
            f"Positive values favor the candidate over `{result.baseline_arm}`.",
            "",
            "| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for question_id, item in scenarios.items():
        assert isinstance(item, dict)
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(
                f"| {item['category']} | {item['family']} | {arm}−{result.baseline_arm} | "
                f"{_distribution_cells(distribution)} | {question_id} |"
            )
    lines.extend(
        [
            "",
            "## Score by family",
            "",
            "| Family | Scenarios | Arm | n | Mean | Median | p95 |",
            "|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    for family, item in families.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(
                f"| {family} | {item['scenario_count']} | {arm} | "
                f"{_distribution_cells(item['arms'][arm])} |"
            )
    lines.extend(
        [
            "",
            "## Paired score deltas by family",
            "",
            f"Positive values favor the candidate over `{result.baseline_arm}`.",
            "",
            "| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |",
            "|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    for family, item in families.items():
        assert isinstance(item, dict)
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(
                f"| {family} | {item['scenario_count']} | {arm}−{result.baseline_arm} | "
                f"{_distribution_cells(distribution)} |"
            )
    return lines


def _timing_overall(result: ScoringResult, overall: dict[str, object]) -> list[str]:
    lines = [
        "",
        "## Overall wall time",
        "",
        "Common-valid paired cells; values are seconds.",
        "",
        "| Arm | n | Mean | Median | p95 |",
        "|---|---:|---:|---:|---:|",
    ]
    for arm in result.arm_order:
        lines.append(f"| {arm} | {_distribution_cells(overall['arms'][arm])} |")
    lines.extend(
        [
            "",
            "### Paired overall wall-time deltas",
            "",
            f"Positive values mean the candidate is slower than `{result.baseline_arm}`.",
            "",
            "| Comparison | n | Mean Δ | Median Δ | p95 Δ |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for arm, distribution in overall["paired_deltas_vs_baseline"].items():
        lines.append(f"| {arm}−{result.baseline_arm} | {_distribution_cells(distribution)} |")
    return lines


def _timing_scenarios(result: ScoringResult, scenarios: dict[str, object]) -> list[str]:
    lines = [
        "",
        "## Wall time by scenario",
        "",
        "| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for question_id, item in scenarios.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(
                f"| {item['category']} | {item['family']} | {arm} | "
                f"{_distribution_cells(item['arms'][arm])} | {question_id} |"
            )
    lines.extend(
        [
            "",
            "## Paired wall-time deltas by scenario",
            "",
            f"Positive values mean the candidate is slower than `{result.baseline_arm}`.",
            "",
            "| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for question_id, item in scenarios.items():
        assert isinstance(item, dict)
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(
                f"| {item['category']} | {item['family']} | {arm}−{result.baseline_arm} | "
                f"{_distribution_cells(distribution)} | {question_id} |"
            )
    return lines


def _timing_families(result: ScoringResult, families: dict[str, object]) -> list[str]:
    lines = [
        "",
        "## Wall time by family",
        "",
        "| Family | Scenarios | Arm | n | Mean | Median | p95 |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for family, item in families.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(
                f"| {family} | {item['scenario_count']} | {arm} | "
                f"{_distribution_cells(item['arms'][arm])} |"
            )
    lines.extend(
        [
            "",
            "## Paired wall-time deltas by family",
            "",
            f"Positive values mean the candidate is slower than `{result.baseline_arm}`.",
            "",
            "| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |",
            "|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    for family, item in families.items():
        assert isinstance(item, dict)
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(
                f"| {family} | {item['scenario_count']} | {arm}−{result.baseline_arm} | "
                f"{_distribution_cells(distribution)} |"
            )
    return lines


def _timing_statistics(result: ScoringResult) -> list[str]:
    timing = timing_statistics(result)
    overall = timing["overall"]
    scenarios = timing["scenarios"]
    families = timing["families"]
    assert isinstance(overall, dict)
    assert isinstance(scenarios, dict)
    assert isinstance(families, dict)
    return [
        *_timing_overall(result, overall),
        *_timing_scenarios(result, scenarios),
        *_timing_families(result, families),
    ]


def render_markdown_report(
    result: ScoringResult,
    config_snapshot: str | None = None,
    observed_hermes: str | None = None,
) -> str:
    lines = [
        "# LiveBench Hermes experiment",
        "",
        f"Common paired coverage: {len(result.common_pairs)}/{result.planned_pairs}",
        "",
        "| Arm | Mean | Median |",
        "|---|---:|---:|",
    ]
    for arm in result.arm_order:
        lines.append(f"| {arm} | {result.arm_means[arm]:.4f} | {_arm_median(result, arm):.4f} |")
    lines.extend(_provenance(config_snapshot, observed_hermes))
    if result.exclusion_counts:
        lines.extend(["", "## Exclusions", ""])
        lines.extend(f"- {code}: {count}" for code, count in result.exclusion_counts.items())
    lines.extend(_statistical_analysis(result))
    lines.extend(_paired_decision_analysis(result))
    lines.extend(_grouped_statistics(result))
    lines.extend(_timing_statistics(result))
    lines.extend(_trace_audit(result))
    return "\n".join(lines) + "\n"
