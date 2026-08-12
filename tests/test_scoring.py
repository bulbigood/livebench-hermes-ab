import json
from pathlib import Path

import pytest

from livebench_hermes_ab.core import ContractError
from livebench_hermes_ab.scoring import (
    render_markdown_report,
    score_run,
    score_standard,
    summary_status,
    timing_summary,
)


def test_cta_oracle_exact_match():
    question = {"task": "cta", "ground_truth": "alpha beta"}
    assert score_standard(question, "alpha beta") == 1.0
    assert score_standard(question, "wrong") == 0.0


def test_old_zebra_oracle_uses_final_answer():
    question = {
        "task": "zebra_puzzle",
        "ground_truth": "red",
        "livebench_release_date": "2024-06-24",
    }
    assert score_standard(question, "Reasoning. Final answer: red") == 1.0


def test_summary_status_preserves_hermes_version_warning():
    manifest = {"hermes_compatibility": {"status": "unverified-version"}}
    assert summary_status(manifest, excluded=False) == "VALID_WITH_HERMES_WARNING"
    assert (
        summary_status(manifest, excluded=True)
        == "VALID_WITH_ONE_INFRA_EXCLUSION_AND_HERMES_WARNING"
    )


def test_summary_status_is_plain_valid_for_verified_hermes():
    manifest = {"hermes_compatibility": {"status": "verified"}}
    assert summary_status(manifest, excluded=False) == "VALID"


def test_streaming_timing_is_marked_but_quality_is_not():
    manifest = {
        "execution_contract": {
            "scheduling": "streaming",
            "effective_workers": 12,
            "timing_comparable": False,
            "timing_note": "* non-strict streaming timing is not paired arm wall-time evidence",
        },
        "execution_result": {"run_makespan_seconds": 9.0},
    }
    answers = {
        "base": [{"total_time_s": 1.0}, {"total_time_s": 3.0}],
        "moa": [{"total_time_s": 4.0}, {"total_time_s": 6.0}],
    }

    timing = timing_summary(manifest, answers)

    assert timing["marker"] == "*"
    assert timing["paired_wall_time_comparable"] is False
    assert timing["run_makespan_seconds"] == 9.0
    assert timing["arms"]["base"]["mean_cell_seconds"] == 2.0
    assert timing["arms"]["base"]["sum_cell_seconds"] == 4.0


def test_balanced_wave_timing_has_no_marker():
    manifest = {
        "execution_contract": {
            "scheduling": "balanced_waves",
            "effective_workers": 6,
            "timing_comparable": True,
            "timing_note": None,
        }
    }
    timing = timing_summary(manifest, {"base": [{"total_time_s": 2.0}]})
    assert timing["marker"] is None
    assert timing["paired_wall_time_comparable"] is True


def test_score_run_revalidates_persisted_moa_traces_and_excludes_degraded_cell(
    tmp_path: Path,
):
    run = tmp_path / "run"
    (run / "raw").mkdir(parents=True)
    trace_dir = run / "homes/moa/moa-traces"
    trace_dir.mkdir(parents=True)
    questions = [
        {"question_id": "q1", "category": "reasoning", "task": "cta", "ground_truth": "a"},
        {"question_id": "q2", "category": "reasoning", "task": "cta", "ground_truth": "b"},
    ]
    (run / "questions.json").write_text(json.dumps(questions))
    hermes = {
        "moa": {
            "enabled": True,
            "active_preset": "default",
            "presets": {
                "default": {
                    "reference_models": [{"provider": "openrouter", "model": "minimax/minimax-m3"}],
                    "aggregator": {
                        "provider": "openai-codex",
                        "model": "gpt-5.6-sol",
                    },
                }
            },
        }
    }
    manifest = {
        "pairs": [
            {"pair_id": "p1", "question_id": "q1", "sample_index": 0},
            {"pair_id": "p2", "question_id": "q2", "sample_index": 0},
        ],
        "arms": {"moa": {"hermes": hermes}},
        "execution_contract": {
            "baseline_arm": "moa",
            "scheduling": "streaming",
            "timing_comparable": False,
        },
        "hermes_compatibility": {"status": "verified"},
    }
    (run / "manifest.json").write_text(json.dumps(manifest))
    records = [_record("q1", "p1", "a"), _record("q2", "p2", "b")]
    (run / "raw/hermes-moa.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records)
    )

    def trace(reference_output: str, aggregate_output: str) -> dict:
        return {
            "preset": "default",
            "references": [
                {
                    "provider": "openrouter",
                    "model": "minimax/minimax-m3",
                    "output": reference_output,
                    "usage": {"input_tokens": 1, "output_tokens": 10_000},
                }
            ],
            "aggregator": {
                "provider": "openai-codex",
                "model": "gpt-5.6-sol",
                "output": aggregate_output,
            },
        }

    (trace_dir / "p1-0.jsonl").write_text(json.dumps(trace("reference", "a")) + "\n")
    (trace_dir / "p2-0.jsonl").write_text(json.dumps(trace("(empty response)", "b")) + "\n")

    summary = score_run(run)

    assert summary["status"] == "VALID_WITH_EXCLUSIONS"
    assert summary["common_valid_pairs"] == 1
    assert summary["exclusions"] == [
        {
            "arm": "moa",
            "pair_id": "p2",
            "question_id": "q2",
            "sample_index": 0,
            "code": "INVALID_MOA_TRACE",
            "reason": "degraded reference output",
        }
    ]


def _record(qid: str, pair_id: str, answer: str) -> dict:
    return {
        "question_id": qid,
        "sample_index": 0,
        "choices": [{"turns": [answer]}],
        "api_info": {"pair_id": pair_id},
        "total_time_s": 1.0,
    }


def _write_two_arm_fixture(run: Path) -> None:
    (run / "raw").mkdir(parents=True)
    questions = [
        {"question_id": "q1", "category": "reasoning", "task": "cta", "ground_truth": "a"},
        {"question_id": "q2", "category": "reasoning", "task": "cta", "ground_truth": "b"},
    ]
    manifest = {
        "pairs": [
            {"pair_id": "p1", "question_id": "q1", "sample_index": 0},
            {"pair_id": "p2", "question_id": "q2", "sample_index": 0},
        ],
        "arms": {
            "base": {"hermes": {"moa": {"enabled": False}}},
            "treatment": {"hermes": {"moa": {"enabled": False}}},
        },
        "arm_order": ["treatment", "base"],
        "execution_contract": {
            "baseline_arm": "base",
            "scheduling": "streaming",
            "timing_comparable": False,
        },
        "hermes_compatibility": {"status": "verified"},
    }
    (run / "questions.json").write_text(json.dumps(questions))
    (run / "manifest.json").write_text(json.dumps(manifest))
    (run / "raw/hermes-base.jsonl").write_text(
        json.dumps(_record("q1", "p1", "a")) + "\n" + json.dumps(_record("q2", "p2", "b")) + "\n"
    )
    (run / "raw/hermes-treatment.jsonl").write_text(json.dumps(_record("q1", "p1", "a")) + "\n")


def test_multiarm_scoring_uses_common_valid_coverage_and_reports_exclusions(tmp_path: Path):
    run = tmp_path / "run"
    _write_two_arm_fixture(run)
    exclusions = {
        "schema_version": 1,
        "excluded_cells": [
            {
                "arm": "treatment",
                "pair_id": "p2",
                "question_id": "q2",
                "sample_index": 0,
                "code": "CELL_TIMEOUT",
                "reason": "timed out after 1800 seconds",
            }
        ],
    }
    (run / "exclusions.json").write_text(json.dumps(exclusions))

    summary = score_run(run)

    assert summary["status"] == "VALID_WITH_EXCLUSIONS"
    assert summary["planned_cells"] == 4
    assert summary["valid_cells"] == 3
    assert summary["excluded_cells"] == 1
    assert summary["planned_pairs"] == 2
    assert summary["common_valid_pairs"] == 1
    assert summary["paired_coverage_fraction"] == 0.5
    assert summary["arm_coverage"]["base"]["valid_cells"] == 2
    assert summary["arm_coverage"]["treatment"]["valid_cells"] == 1
    assert summary["arms"] == ["treatment", "base"]
    report = (run / "report.md").read_text()
    treatment_row = report.index("| `treatment` |")
    base_row = report.index("| `base` |")
    assert treatment_row < base_row
    assert "## ⚠ Timing warning" in report
    assert "prepare --balanced-waves" in report
    assert "run --balanced-waves" in report


def test_markdown_report_marks_balanced_wave_timing_as_comparable():
    manifest = {
        "experiment_id": "example",
        "execution_contract": {"scheduling": "balanced_waves", "timing_comparable": True},
    }
    summary = {
        "status": "VALID",
        "baseline_arm": "base",
        "arms": ["base"],
        "planned_pairs": 1,
        "common_valid_pairs": 1,
        "paired_coverage_fraction": 1.0,
        "planned_cells": 1,
        "valid_cells": 1,
        "excluded_cells": 0,
        "arm_coverage": {"base": {"planned_cells": 1, "valid_cells": 1, "excluded_cells": 0}},
        "arm_means": {"base": 1.0},
        "comparisons_vs_baseline": {},
        "category_means": {"base": {"reasoning": 1.0}},
        "timing": {
            "paired_wall_time_comparable": True,
            "run_makespan_seconds": 1.0,
            "arms": {"base": {"mean_cell_seconds": 1.0, "sum_cell_seconds": 1.0, "cells": 1}},
        },
        "exclusions": [],
        "hermes_compatibility": {"status": "verified", "version": "0.19.1"},
        "scores_sha256": "abc",
    }

    report = render_markdown_report(summary, manifest)

    assert "## ⚠ Timing warning" not in report
    assert "complete-arm wave barriers" in report


def test_scoring_rejects_manifest_arm_order_drift(tmp_path: Path):
    run = tmp_path / "run"
    _write_two_arm_fixture(run)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["arm_order"] = ["base", "unknown"]
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ContractError, match="arm_order"):
        score_run(run)


def test_multiarm_scoring_rejects_unexplained_missing_cell(tmp_path: Path):
    run = tmp_path / "run"
    _write_two_arm_fixture(run)

    with pytest.raises(ContractError, match="unexplained missing cells"):
        score_run(run)


def test_malformed_moa_trace_is_an_explicit_cell_exclusion(tmp_path: Path):
    run = tmp_path / "run"
    _write_two_arm_fixture(run)
    (run / "raw/hermes-treatment.jsonl").write_text(
        json.dumps(_record("q1", "p1", "a")) + "\n" + json.dumps(_record("q2", "p2", "b")) + "\n"
    )
    manifest = json.loads((run / "manifest.json").read_text())
    hermes = {
        "moa": {
            "enabled": True,
            "active_preset": "default",
            "presets": {
                "default": {
                    "reference_models": [{"provider": "openrouter", "model": "minimax/minimax-m3"}],
                    "aggregator": {"provider": "openai-codex", "model": "gpt-5.6-sol"},
                }
            },
        }
    }
    manifest["arms"]["treatment"]["hermes"] = hermes
    (run / "manifest.json").write_text(json.dumps(manifest))
    trace_dir = run / "homes/treatment/moa-traces"
    trace_dir.mkdir(parents=True)
    (trace_dir / "p1-0.jsonl").write_text("{broken\n")
    valid_trace = {
        "preset": "default",
        "references": [
            {
                "provider": "openrouter",
                "model": "minimax/minimax-m3",
                "output": "reference",
                "usage": {"input_tokens": 1, "output_tokens": 2},
            }
        ],
        "aggregator": {
            "provider": "openai-codex",
            "model": "gpt-5.6-sol",
            "output": "b",
        },
    }
    (trace_dir / "p2-0.jsonl").write_text(json.dumps(valid_trace) + "\n")

    summary = score_run(run)

    assert summary["common_valid_pairs"] == 1
    assert summary["exclusions"][0]["pair_id"] == "p1"
    assert summary["exclusions"][0]["code"] == "INVALID_MOA_TRACE"
    assert "malformed trace JSON" in summary["exclusions"][0]["reason"]
