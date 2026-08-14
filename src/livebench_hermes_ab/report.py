from __future__ import annotations

import statistics
from collections.abc import Mapping

import yaml

from .scoring import (
    ScoringResult,
    grouped_statistics,
    missing_data_sensitivity,
    paired_decision_analysis,
    planned_contrast_analysis,
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
        "Catastrophic harm means a paired score delta `<= -0.5`.",
        "",
        "| Candidate vs baseline | n | Mean delta | Median delta | Harm rate | Catastrophic harm rate | 95% CI | Verdict | Projected CI-excluding-zero samples/scenario | 95% power samples/scenario |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
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
            f"{float(item['harm_rate']):.1%} | "
            f"{float(item['catastrophic_harm_rate']):.1%} | "
            f"{rendered_interval} | {item['verdict']} | "
            f"{'Unavailable' if projected is None else projected} | "
            f"{'Unavailable' if powered is None else powered} |"
        )
    return lines


def _planned_contrasts(result: ScoringResult) -> list[str]:
    if not result.contrasts:
        return []
    analysis = planned_contrast_analysis(result)
    comparisons = analysis["comparisons"]
    assert isinstance(comparisons, dict)
    scores = {
        arm: {row.pair_id: row.score for row in result.rows if row.arm == arm}
        for arm in result.arm_order
    }
    lines = [
        "",
        "## Planned paired contrasts",
        "",
        "These contrasts were frozen in the experiment configuration before scoring.",
        "",
        "| Contrast | n | Mean delta | Median delta | Harm rate | Catastrophic harm rate | 95% CI | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in comparisons.values():
        assert isinstance(item, dict)
        left, right = str(item["left_arm"]), str(item["right_arm"])
        pair_ids = sorted(scores[left].keys() & scores[right].keys())
        differences = [scores[left][pair] - scores[right][pair] for pair in pair_ids]
        interval = item["confidence_interval"]
        rendered_interval = (
            "Unavailable" if interval is None
            else f"[{float(interval[0]):.4f}, {float(interval[1]):.4f}]"
        )
        lines.append(
            f"| {left} vs {right} | {item['observations']} | "
            f"{float(item['observed_mean_delta']):.4f} | {statistics.median(differences):.4f} | "
            f"{float(item['harm_rate']):.1%} | "
            f"{float(item['catastrophic_harm_rate']):.1%} | {rendered_interval} | "
            f"{item['verdict']} |"
        )
    return lines


def _missing_data_sensitivity(result: ScoringResult) -> list[str]:
    analysis = missing_data_sensitivity(result)
    comparisons = analysis["comparisons"]
    assert isinstance(comparisons, dict)
    lines = [
        "",
        "## Missing-data sensitivity",
        "",
        "The score and confidence-interval tables above are complete-case estimates conditional on every arm returning a valid output. Missingness is not assumed random. The bounds below assign every missing paired delta its worst possible value under the stated `[0, 1]` score range.",
        "",
        "| Contrast | Observed pairs | Missing pairs | Worst-case mean-delta bounds |",
        "|---|---:|---:|---:|",
    ]
    for key, value in comparisons.items():
        assert isinstance(value, dict)
        lines.append(
            f"| {key} | {value['observed_pairs']} | {value['missing_pairs']} | "
            f"[{float(value['lower_mean_delta']):.4f}, "
            f"{float(value['upper_mean_delta']):.4f}] |"
        )
    return lines


def _mechanism_statistics(result: ScoringResult) -> list[str]:
    summary = result.mechanism_statistics
    by_arm = summary.get("by_arm")
    if not isinstance(by_arm, dict) or not by_arm:
        return []
    lines = [
        "",
        "## Mechanism proxies",
        "",
        str(summary.get("proxy_warning") or ""),
        "",
        "| Arm | Trace cells | Reference outputs | Candidate present | Candidate scorable | Candidate score mean | Exact adoption | Useful adoption | Erroneous adoption | Structural violations | Underdetermination signals | Wrapper present |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, value in by_arm.items():
        assert isinstance(value, dict)
        mean = value.get("candidate_score_mean")
        lines.append(
            f"| {arm} | {value.get('trace_cells', 0)} | {value.get('reference_outputs', 0)} | "
            f"{value.get('candidate_present', 0)} | {value.get('candidate_scorable', 0)} | "
            f"{'Unavailable' if mean is None else f'{float(mean):.4f}'} | "
            f"{value.get('candidate_exact_adoption', 0)} | "
            f"{value.get('useful_candidate_adoption', 0)} | "
            f"{value.get('erroneous_candidate_adoption', 0)} | "
            f"{value.get('structural_violation_outputs', 0)} | "
            f"{value.get('underdetermination_signal_outputs', 0)} | "
            f"{value.get('untrusted_wrapper_present', 0)} |"
        )
    return lines


def _billing_summary(result: ScoringResult) -> list[str]:
    summary = result.billing_summary
    groups = summary.get("groups")
    if not isinstance(groups, list):
        return []
    lines = [
        "",
        "## Provider usage and billing completeness",
        "",
        f"- Evidence source: {summary.get('source')}",
        f"- Complete: {summary.get('complete')}",
        f"- Recorded calls: {summary.get('recorded_calls', 0)}",
        f"- Cells/attempts without a provider ledger: {summary.get('cells_without_provider_ledger', 0)}",
        f"- Usage-complete calls: {summary.get('usage_complete_calls', 0)}",
        f"- Cost-complete calls: {summary.get('cost_complete_calls', 0)}",
        f"- Calls with provider generation IDs: {summary.get('generation_id_calls', 0)}",
        "",
        "| Arm | Role | Provider | Model | Status | Calls | Input | Output | Reasoning | Cache read | Cache write | Estimated USD | Actual USD |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for value in groups:
        assert isinstance(value, dict)
        estimated = value.get("estimated_cost_usd")
        actual = value.get("actual_cost_usd")
        estimated_text = "unknown" if estimated is None else f"{float(estimated):.10f}"
        actual_text = "unknown" if actual is None else f"{float(actual):.10f}"
        lines.append(
            f"| {value['arm']} | {value['role']} | {value['provider']} | {value['model']} | "
            f"{value['status']} | {value['calls']} | {value['input_tokens']} | "
            f"{value['output_tokens']} | {value['reasoning_tokens']} | "
            f"{value['cache_read_tokens']} | {value['cache_write_tokens']} | "
            f"{estimated_text} | {actual_text} |"
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


def _distribution_cells(value: Mapping[str, object]) -> str:
    if int(value["n"]) == 0:
        return "0 | — | — | —"
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
    lines.extend(_planned_contrasts(result))
    lines.extend(_missing_data_sensitivity(result))
    lines.extend(_grouped_statistics(result))
    lines.extend(_timing_statistics(result))
    lines.extend(_mechanism_statistics(result))
    lines.extend(_billing_summary(result))
    lines.extend(_trace_audit(result))
    return "\n".join(lines) + "\n"
