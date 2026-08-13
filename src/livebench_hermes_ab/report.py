from __future__ import annotations

from .scoring import ScoringResult, grouped_statistics, timing_statistics


def _statistic(value: float | None) -> str:
    return "Unavailable" if value is None else f"{value:.6f}"


def _statistical_analysis(result: ScoringResult) -> list[str]:
    lines = [
        "",
        "## Statistical analysis",
        "",
        f"Configured samples per task: {result.samples_per_task}",
        f"Minimum common-valid samples per task: {result.minimum_common_samples_per_task}",
        f"Confidence level: {result.confidence_level:.0%}",
        f"Target margin of error: ±{result.target_margin_of_error:.4f}",
        "",
    ]
    if result.minimum_common_samples_per_task < 5:
        lines.extend(
            [
                (
                    "> WARNING: minimum common-valid samples per task is "
                    f"{result.minimum_common_samples_per_task}; fewer than 5 samples are "
                    "insufficient for a stable variance-based sample-size estimate."
                ),
                "Recommended samples/task | Unavailable",
                "",
            ]
        )
    lines.extend(
        [
            (
                f"| Arm | n | Tasks | Sample variance | Std. dev. | Std. error | "
                f"{result.confidence_level:.0%} CI | "
                "Within-task variance | Recommended samples/task |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for arm in result.arm_order:
        item = result.arm_statistics[arm]
        interval = (
            "Unavailable"
            if item.confidence_interval is None
            else f"[{item.confidence_interval[0]:.4f}, {item.confidence_interval[1]:.4f}]"
        )
        recommended = (
            "Unavailable"
            if item.recommended_samples_per_task is None
            else str(item.recommended_samples_per_task)
        )
        lines.append(
            f"| {arm} | {item.observations} | {item.tasks} | "
            f"{_statistic(item.sample_variance)} | {_statistic(item.standard_deviation)} | "
            f"{_statistic(item.standard_error)} | {interval} | "
            f"{_statistic(item.pooled_within_task_variance)} | {recommended} |"
        )
    if result.minimum_common_samples_per_task >= 5:
        recommendations = [
            item.recommended_samples_per_task
            for item in result.arm_statistics.values()
            if item.recommended_samples_per_task is not None
        ]
        lines.extend(
            [
                "",
                f"Overall recommended samples/task: {max(recommendations)}",
                "",
                (
                    "Recommended sample counts are pilot estimates for the configured margin of "
                    "error. Zero or unavailable observed within-task variance uses a conservative "
                    "[0,1] score-range bound."
                ),
            ]
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
    deviation = value["sample_standard_deviation"]
    values = [str(value["n"]), f"{float(value['mean']):.4f}", "—" if deviation is None else f"{float(deviation):.4f}"]
    values.extend(f"{float(percentiles[key]):.4f}" for key in ("p05", "p25", "p50", "p75", "p95"))
    return " | ".join(values)


def _grouped_statistics(result: ScoringResult) -> list[str]:
    grouped = grouped_statistics(result)
    scenarios, families = grouped["scenarios"], grouped["families"]
    assert isinstance(scenarios, dict) and isinstance(families, dict)
    lines = [
        "", "## Per-scenario statistics and percentiles", "",
        "| Scenario | Category | Family | Arm/paired delta | n | Mean | SD | p05 | p25 | p50 | p75 | p95 |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for question_id, item in scenarios.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(f"| {question_id} | {item['category']} | {item['family']} | {arm} | {_distribution_cells(item['arms'][arm])} |")
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(f"| {question_id} | {item['category']} | {item['family']} | Δ {arm}−{result.baseline_arm} | {_distribution_cells(distribution)} |")
    lines.extend([
        "", "## Per-family statistics and percentiles", "",
        "| Family | Scenarios | Arm/paired delta | n | Mean | SD | p05 | p25 | p50 | p75 | p95 |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for family, item in families.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(f"| {family} | {item['scenario_count']} | {arm} | {_distribution_cells(item['arms'][arm])} |")
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(f"| {family} | {item['scenario_count']} | Δ {arm}−{result.baseline_arm} | {_distribution_cells(distribution)} |")
    return lines


def _timing_statistics(result: ScoringResult) -> list[str]:
    timing = timing_statistics(result)
    overall = timing["overall"]
    assert isinstance(overall, dict)
    lines = [
        "", "## Overall wall-time statistics", "",
        "Timings use common-valid paired cells. Values are seconds; sums are cell-seconds, not pipeline elapsed time.", "",
        "| Arm/paired delta | n | Mean | SD | Sum | p05 | p25 | p50 | p75 | p95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def timing_cells(value: dict[str, object]) -> str:
        cells = _distribution_cells(value).split(" | ")
        cells.insert(3, f"{float(value['sum_seconds']):.4f}")
        return " | ".join(cells)

    for arm in result.arm_order:
        lines.append(f"| {arm} | {timing_cells(overall['arms'][arm])} |")
    for arm, distribution in overall["paired_deltas_vs_baseline"].items():
        lines.append(f"| Δ {arm}−{result.baseline_arm} | {timing_cells(distribution)} |")
    lines.extend([
        "", "## Per-scenario wall-time statistics", "",
        "| Scenario | Category | Family | Arm/paired delta | n | Mean | SD | Sum | p05 | p25 | p50 | p75 | p95 |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    scenarios = timing["scenarios"]
    assert isinstance(scenarios, dict)
    for question_id, item in scenarios.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(f"| {question_id} | {item['category']} | {item['family']} | {arm} | {timing_cells(item['arms'][arm])} |")
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(f"| {question_id} | {item['category']} | {item['family']} | Δ {arm}−{result.baseline_arm} | {timing_cells(distribution)} |")
    lines.extend([
        "", "## Per-family wall-time statistics", "",
        "| Family | Scenarios | Arm/paired delta | n | Mean | SD | Sum | p05 | p25 | p50 | p75 | p95 |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    families = timing["families"]
    assert isinstance(families, dict)
    for family, item in families.items():
        assert isinstance(item, dict)
        for arm in result.arm_order:
            lines.append(f"| {family} | {item['scenario_count']} | {arm} | {timing_cells(item['arms'][arm])} |")
        for arm, distribution in item["paired_deltas_vs_baseline"].items():
            lines.append(f"| {family} | {item['scenario_count']} | Δ {arm}−{result.baseline_arm} | {timing_cells(distribution)} |")
    return lines


def render_markdown_report(result: ScoringResult) -> str:
    lines = [
        "# LiveBench Hermes experiment",
        "",
        f"Common paired coverage: {len(result.common_pairs)}/{result.planned_pairs}",
        "",
        "| Arm | Mean | Delta vs baseline |",
        "|---|---:|---:|",
    ]
    for arm in result.arm_order:
        delta = "—" if arm == result.baseline_arm else f"{result.comparisons[arm]:.4f}"
        lines.append(f"| {arm} | {result.arm_means[arm]:.4f} | {delta} |")
    if result.exclusion_counts:
        lines.extend(["", "## Exclusions", ""])
        lines.extend(f"- {code}: {count}" for code, count in result.exclusion_counts.items())
    lines.extend(_statistical_analysis(result))
    lines.extend(_grouped_statistics(result))
    lines.extend(_timing_statistics(result))
    lines.extend(_trace_audit(result))
    return "\n".join(lines) + "\n"
