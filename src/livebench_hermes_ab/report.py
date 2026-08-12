from __future__ import annotations

from .scoring import ScoringResult


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
    lines.extend(
        [
            "",
            "## Trace audit",
            "",
            f"- Valid traces: {result.trace_audit['valid_traces']}",
            f"- Invalid traces: {result.trace_audit['invalid_traces']}",
            f"- Reference calls: {result.trace_audit['reference_calls']}",
            f"- Reference input tokens: {result.trace_audit['reference_input_tokens']}",
            f"- Reference output tokens: {result.trace_audit['reference_output_tokens']}",
        ]
    )
    return "\n".join(lines) + "\n"
