from __future__ import annotations

from .scoring import ScoringResult


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
    lines.extend(_trace_audit(result))
    return "\n".join(lines) + "\n"
