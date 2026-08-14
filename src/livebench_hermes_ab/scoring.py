from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist
from types import MappingProxyType

from .artifacts import ScoringBundle
from .domain import CellOutcome, ExcludedOutcome, IntegrityError, ValidOutcome
from .trace_validation import ExpectedTrace, validate_cell_trace

ScoreAdapter = Callable[[Mapping[str, object], str], float]


@dataclass(frozen=True, slots=True)
class QuestionEvidence:
    category: str
    task: str
    raw: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class FrozenRun:
    arm_order: tuple[str, ...]
    baseline_arm: str
    planned_pairs: tuple[str, ...]
    outcomes: tuple[CellOutcome, ...]
    questions: Mapping[str, QuestionEvidence]
    samples_per_task: int = 1
    confidence_level: float = 0.95
    target_margin_of_error: float = 0.05


@dataclass(frozen=True, slots=True)
class ScoreRow:
    pair_id: str
    question_id: str
    category: str
    family: str
    arm: str
    score: float
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class ArmStatistics:
    observations: int
    tasks: int
    sample_variance: float | None
    standard_deviation: float | None
    standard_error: float | None
    confidence_interval: tuple[float, float] | None
    pooled_within_task_variance: float | None
    recommended_samples_per_task: int | None
    recommendation_basis: str | None


@dataclass(frozen=True, slots=True)
class ScoringResult:
    arm_order: tuple[str, ...]
    baseline_arm: str
    planned_pairs: int
    common_pairs: tuple[str, ...]
    rows: tuple[ScoreRow, ...]
    arm_means: Mapping[str, float]
    comparisons: Mapping[str, float]
    exclusion_counts: Mapping[str, int]
    trace_audit: Mapping[str, int]
    samples_per_task: int
    minimum_common_samples_per_task: int
    arm_statistics: Mapping[str, ArmStatistics]
    confidence_level: float = 0.95
    target_margin_of_error: float = 0.05


def _arm_statistics(
    rows: tuple[ScoreRow, ...],
    arm_order: tuple[str, ...],
    samples_per_task: int,
    minimum_common_samples_per_task: int,
    confidence_level: float = 0.95,
    target_margin_of_error: float = 0.05,
) -> Mapping[str, ArmStatistics]:
    if samples_per_task < 1:
        raise IntegrityError("samples per task must be positive")
    z = NormalDist().inv_cdf(0.5 + confidence_level / 2)
    result: dict[str, ArmStatistics] = {}
    for arm in arm_order:
        arm_rows = [row for row in rows if row.arm == arm]
        values = [row.score for row in arm_rows]
        variance = statistics.variance(values) if len(values) >= 2 else None
        deviation = math.sqrt(variance) if variance is not None else None
        error = deviation / math.sqrt(len(values)) if deviation is not None else None
        mean = statistics.fmean(values)
        interval = (mean - z * error, mean + z * error) if error is not None else None

        by_question: dict[str, list[float]] = defaultdict(list)
        for row in arm_rows:
            by_question[row.question_id].append(row.score)
        degrees = sum(len(group) - 1 for group in by_question.values() if len(group) >= 2)
        pooled = (
            sum(
                (len(group) - 1) * statistics.variance(group)
                for group in by_question.values()
                if len(group) >= 2
            )
            / degrees
            if degrees
            else None
        )
        recommended = None
        basis = None
        if minimum_common_samples_per_task >= 5:
            planning_variance = pooled
            basis = "observed pooled within-task variance"
            if planning_variance is None or planning_variance == 0:
                planning_variance = 0.25
                basis = "conservative [0,1] score-range variance bound"
            estimated = math.ceil(
                z * z * planning_variance / (len(by_question) * target_margin_of_error**2)
            )
            recommended = max(samples_per_task, estimated)
        result[arm] = ArmStatistics(
            len(values),
            len(by_question),
            variance,
            deviation,
            error,
            interval,
            pooled,
            recommended,
            basis,
        )
    return MappingProxyType(result)


def reconcile_scoring_evidence(
    run: FrozenRun,
) -> tuple[tuple[str, ...], Mapping[tuple[str, str], ValidOutcome]]:
    if run.baseline_arm not in run.arm_order or not run.arm_order:
        raise IntegrityError("invalid arm order or baseline")
    planned = set(run.planned_pairs)
    if len(planned) != len(run.planned_pairs):
        raise IntegrityError("duplicate planned pair")
    terminal: dict[tuple[str, str], CellOutcome] = {}
    for outcome in run.outcomes:
        key = (outcome.cell.arm, outcome.cell.pair_id)
        if outcome.cell.arm not in run.arm_order or outcome.cell.pair_id not in planned:
            raise IntegrityError("outcome outside planned matrix")
        if key in terminal:
            raise IntegrityError("duplicate terminal outcome")
        terminal[key] = outcome
    missing = [
        (arm, pair)
        for arm in run.arm_order
        for pair in run.planned_pairs
        if (arm, pair) not in terminal
    ]
    if missing:
        raise IntegrityError(f"missing terminal outcomes: {len(missing)}")
    valid = {key: value for key, value in terminal.items() if isinstance(value, ValidOutcome)}
    common = tuple(
        pair for pair in run.planned_pairs if all((arm, pair) in valid for arm in run.arm_order)
    )
    if not common:
        raise IntegrityError("no common valid pairs remain")
    return common, MappingProxyType(valid)


def score_run(run: FrozenRun, adapters: Mapping[str, ScoreAdapter]) -> ScoringResult:
    common, valid = reconcile_scoring_evidence(run)
    rows: list[ScoreRow] = []
    by_arm: dict[str, list[float]] = defaultdict(list)
    for pair in common:
        first = valid[(run.arm_order[0], pair)]
        question = run.questions.get(first.cell.question_id)
        if question is None:
            raise IntegrityError(f"missing question: {first.cell.question_id}")
        adapter = adapters.get(question.task)
        if adapter is None:
            raise IntegrityError(f"no scoring adapter for task: {question.task}")
        for arm in run.arm_order:
            outcome = valid[(arm, pair)]
            answer = _answer_text(outcome.answer_record)
            score = float(adapter(question.raw, answer))
            if outcome.elapsed_seconds is None:
                raise IntegrityError("valid outcome missing elapsed_seconds")
            rows.append(
                ScoreRow(
                    pair,
                    outcome.cell.question_id,
                    question.category,
                    question.task,
                    arm,
                    score,
                    outcome.elapsed_seconds,
                )
            )
            by_arm[arm].append(score)
    means = {arm: sum(by_arm[arm]) / len(by_arm[arm]) for arm in run.arm_order}
    comparisons = {
        arm: means[arm] - means[run.baseline_arm]
        for arm in run.arm_order
        if arm != run.baseline_arm
    }
    exclusions = Counter(
        outcome.code.value for outcome in run.outcomes if isinstance(outcome, ExcludedOutcome)
    )
    audits = _revalidate_trace_audits(run.outcomes)
    trace_audit = {
        "valid_traces": len(audits),
        "reference_calls": sum(int(item.get("reference_calls", 0)) for item in audits),
        "reference_input_tokens": sum(
            int(item.get("reference_input_tokens", 0)) for item in audits
        ),
        "reference_output_tokens": sum(
            int(item.get("reference_output_tokens", 0)) for item in audits
        ),
        "invalid_traces": exclusions.get("INVALID_MOA_TRACE", 0),
    }
    row_values = tuple(rows)
    common_counts = Counter(row.question_id for row in row_values if row.arm == run.baseline_arm)
    minimum_common_samples = min(common_counts.values())
    return ScoringResult(
        run.arm_order,
        run.baseline_arm,
        len(run.planned_pairs),
        common,
        row_values,
        MappingProxyType(means),
        MappingProxyType(comparisons),
        MappingProxyType(dict(sorted(exclusions.items()))),
        MappingProxyType(trace_audit),
        run.samples_per_task,
        minimum_common_samples,
        _arm_statistics(
            row_values,
            run.arm_order,
            run.samples_per_task,
            minimum_common_samples,
            run.confidence_level,
            run.target_margin_of_error,
        ),
        run.confidence_level,
        run.target_margin_of_error,
    )


def _revalidate_trace_audits(outcomes: tuple[CellOutcome, ...]) -> list[Mapping[str, object]]:
    audits: list[Mapping[str, object]] = []
    for outcome in outcomes:
        if not isinstance(outcome, ValidOutcome):
            continue
        for audit in outcome.answer_record.get("trace_audit", []):  # type: ignore[union-attr]
            if not isinstance(audit, Mapping):
                raise IntegrityError("invalid persisted trace audit")
            expected = audit.get("expected")
            if not isinstance(expected, Mapping):
                raise IntegrityError("persisted trace expectation is missing")
            try:
                expectation = ExpectedTrace(
                    outcome.cell,
                    str(expected["preset"]),
                    tuple((str(item[0]), str(item[1])) for item in expected["references"]),
                    (str(expected["aggregator"][0]), str(expected["aggregator"][1])),
                )
                validation = validate_cell_trace(
                    str(audit["trace"]).encode(), expectation, str(audit["answer"])
                )
            except (KeyError, IndexError, TypeError) as exc:
                raise IntegrityError("invalid persisted trace evidence") from exc
            if validation.exclusion is not None or validation.usage is None:
                reason = (
                    validation.exclusion.reason if validation.exclusion else "unknown trace error"
                )
                raise IntegrityError(f"persisted trace failed revalidation: {reason}")
            usage = validation.usage
            audits.append(
                {
                    "reference_calls": usage.reference_calls,
                    "reference_input_tokens": usage.reference_input_tokens,
                    "reference_output_tokens": usage.reference_output_tokens,
                }
            )
    return audits


def _answer_text(record: Mapping[str, object]) -> str:
    if isinstance(record.get("answer"), str) and str(record["answer"]).strip():
        return str(record["answer"])
    try:
        turns = record["choices"][0]["turns"]  # type: ignore[index]
        answer = str(turns[-1])
        if answer.strip():
            return answer
    except (KeyError, IndexError, TypeError):
        pass
    raise IntegrityError("invalid answer record")


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _distribution(values: list[float]) -> dict[str, object]:
    if not values:
        raise IntegrityError("cannot summarize an empty score distribution")
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "sample_standard_deviation": statistics.stdev(values) if len(values) >= 2 else None,
        "percentiles": {
            name: _percentile(values, probability)
            for name, probability in (
                ("p05", 0.05), ("p25", 0.25), ("p50", 0.50),
                ("p75", 0.75), ("p95", 0.95),
            )
        },
    }


def grouped_statistics(result: ScoringResult) -> dict[str, object]:
    baseline = result.baseline_arm
    scenarios: dict[str, object] = {}
    families: dict[str, object] = {}
    for question_id in sorted({row.question_id for row in result.rows}):
        rows = [row for row in result.rows if row.question_id == question_id]
        baseline_by_pair = {row.pair_id: row.score for row in rows if row.arm == baseline}
        scenarios[question_id] = {
            "category": rows[0].category,
            "family": rows[0].family,
            "arms": {
                arm: _distribution([row.score for row in rows if row.arm == arm])
                for arm in result.arm_order
            },
            "paired_deltas_vs_baseline": {
                arm: _distribution([
                    row.score - baseline_by_pair[row.pair_id]
                    for row in rows if row.arm == arm
                ])
                for arm in result.arm_order if arm != baseline
            },
        }
    for family in sorted({row.family for row in result.rows}):
        rows = [row for row in result.rows if row.family == family]
        baseline_by_pair = {row.pair_id: row.score for row in rows if row.arm == baseline}
        families[family] = {
            "categories": sorted({row.category for row in rows}),
            "scenario_count": len({row.question_id for row in rows}),
            "arms": {
                arm: _distribution([row.score for row in rows if row.arm == arm])
                for arm in result.arm_order
            },
            "paired_deltas_vs_baseline": {
                arm: _distribution([
                    row.score - baseline_by_pair[row.pair_id]
                    for row in rows if row.arm == arm
                ])
                for arm in result.arm_order if arm != baseline
            },
        }
    return {"scenarios": scenarios, "families": families}


def _timing_distribution(values: list[float]) -> dict[str, object]:
    result = _distribution(values)
    result["sum_seconds"] = sum(values)
    return result


def timing_statistics(result: ScoringResult) -> dict[str, object]:
    baseline = result.baseline_arm

    def group(rows: list[ScoreRow]) -> dict[str, object]:
        baseline_by_pair = {
            row.pair_id: row.elapsed_seconds for row in rows if row.arm == baseline
        }
        return {
            "arms": {
                arm: _timing_distribution(
                    [row.elapsed_seconds for row in rows if row.arm == arm]
                )
                for arm in result.arm_order
            },
            "paired_deltas_vs_baseline": {
                arm: _timing_distribution([
                    row.elapsed_seconds - baseline_by_pair[row.pair_id]
                    for row in rows if row.arm == arm
                ])
                for arm in result.arm_order if arm != baseline
            },
        }

    scenarios: dict[str, object] = {}
    for question_id in sorted({row.question_id for row in result.rows}):
        rows = [row for row in result.rows if row.question_id == question_id]
        scenarios[question_id] = {
            "category": rows[0].category,
            "family": rows[0].family,
            **group(rows),
        }
    families: dict[str, object] = {}
    for family in sorted({row.family for row in result.rows}):
        rows = [row for row in result.rows if row.family == family]
        families[family] = {
            "categories": sorted({row.category for row in rows}),
            "scenario_count": len({row.question_id for row in rows}),
            **group(rows),
        }
    return {
        "cohort": "common_valid_pairs",
        "unit": "seconds",
        "overall": group(list(result.rows)),
        "scenarios": scenarios,
        "families": families,
    }


def paired_decision_analysis(result: ScoringResult) -> dict[str, object]:
    confidence_level = 0.95
    power = 0.95
    catastrophic_harm_threshold = -0.5
    alpha = 1.0 - confidence_level
    z_alpha = statistics.NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_power = statistics.NormalDist().inv_cdf(power)
    baseline = result.baseline_arm
    task_count = len({row.question_id for row in result.rows})
    baseline_by_pair = {
        row.pair_id: row.score for row in result.rows if row.arm == baseline
    }
    comparisons: dict[str, object] = {}
    for arm in result.arm_order:
        if arm == baseline:
            continue
        differences = [
            row.score - baseline_by_pair[row.pair_id]
            for row in result.rows if row.arm == arm
        ]
        observations = len(differences)
        harm_count = sum(difference < 0 for difference in differences)
        catastrophic_harm_count = sum(
            difference <= catastrophic_harm_threshold for difference in differences
        )
        mean = statistics.fmean(differences)
        deviation = statistics.stdev(differences) if observations >= 2 else None
        standard_error = deviation / math.sqrt(observations) if deviation is not None else None
        interval = (
            [mean - z_alpha * standard_error, mean + z_alpha * standard_error]
            if standard_error is not None else None
        )
        verdict = (
            "unavailable" if interval is None else
            "better" if interval[0] > 0 else
            "worse" if interval[1] < 0 else "inconclusive"
        )
        projected_pairs = power_pairs = None
        if deviation is not None and mean != 0:
            projected_pairs = max(2, math.ceil((z_alpha * deviation / abs(mean)) ** 2))
            power_pairs = max(2, math.ceil(((z_alpha + z_power) * deviation / abs(mean)) ** 2))
        comparisons[arm] = {
            "confidence_level": confidence_level,
            "power": power,
            "two_sided_alpha": alpha,
            "observations": observations,
            "harm_count": harm_count,
            "harm_rate": harm_count / observations,
            "catastrophic_harm_threshold": catastrophic_harm_threshold,
            "catastrophic_harm_count": catastrophic_harm_count,
            "catastrophic_harm_rate": catastrophic_harm_count / observations,
            "observed_mean_delta": mean,
            "sample_standard_deviation": deviation,
            "standard_error": standard_error,
            "confidence_interval": interval,
            "verdict": verdict,
            "required_total_pairs_for_projected_ci_excluding_zero": projected_pairs,
            "required_samples_per_scenario_for_projected_ci_excluding_zero": (
                math.ceil(projected_pairs / task_count) if projected_pairs is not None else None
            ),
            "required_total_pairs_for_95_percent_power": power_pairs,
            "required_samples_per_scenario_for_95_percent_power": (
                math.ceil(power_pairs / task_count) if power_pairs is not None else None
            ),
        }
    return {
        "method": "normal_approximation_on_common_valid_paired_differences",
        "assumption": "future effect size and paired-difference variance match this run",
        "comparisons": comparisons,
    }


def scoring_bundle(result: ScoringResult, report: str) -> ScoringBundle:
    statistics_value = {
        arm: {
            "observations": item.observations,
            "tasks": item.tasks,
            "sample_variance": item.sample_variance,
            "standard_deviation": item.standard_deviation,
            "standard_error": item.standard_error,
            "confidence_interval": list(item.confidence_interval)
            if item.confidence_interval is not None
            else None,
            "pooled_within_task_variance": item.pooled_within_task_variance,
            "recommended_samples_per_task": item.recommended_samples_per_task,
            "recommendation_basis": item.recommendation_basis,
        }
        for arm, item in result.arm_statistics.items()
    }
    recommendations = [
        item.recommended_samples_per_task
        for item in result.arm_statistics.values()
        if item.recommended_samples_per_task is not None
    ]
    summary = {
        "schema_version": 2,
        "baseline_arm": result.baseline_arm,
        "arm_order": list(result.arm_order),
        "planned_pairs": result.planned_pairs,
        "common_valid_pairs": len(result.common_pairs),
        "paired_coverage_fraction": len(result.common_pairs) / result.planned_pairs,
        "arm_means": dict(result.arm_means),
        "comparisons_vs_baseline": dict(result.comparisons),
        "exclusion_counts": dict(result.exclusion_counts),
        "trace_audit": dict(result.trace_audit),
        "samples_per_task": result.samples_per_task,
        "minimum_common_samples_per_task": result.minimum_common_samples_per_task,
        "statistical_analysis": {
            "confidence_level": result.confidence_level,
            "target_margin_of_error": result.target_margin_of_error,
            "sufficient_pilot_samples": result.minimum_common_samples_per_task >= 5,
            "recommended_samples_per_task": max(recommendations) if recommendations else None,
            "arms": statistics_value,
        },
        "grouped_statistics": grouped_statistics(result),
        "timing_statistics": timing_statistics(result),
        "paired_decision_analysis": paired_decision_analysis(result),
    }
    scores = [
        {"pair_id": row.pair_id, "question_id": row.question_id, "category": row.category,
         "family": row.family, "arm": row.arm, "score": row.score,
         "elapsed_seconds": row.elapsed_seconds}
        for row in result.rows
    ]
    encode = lambda value: (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )
    return ScoringBundle(
        {
            Path("summary.json"): encode(summary),
            Path("scores.json"): encode(scores),
            Path("report.md"): report.encode(),
        }
    )
