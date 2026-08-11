import json
from pathlib import Path

import pytest

from livebench_hermes_ab.core import ContractError
from livebench_hermes_ab.scoring import score_run, score_standard, summary_status, timing_summary


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


def test_score_run_revalidates_persisted_moa_traces(tmp_path: Path):
    run = tmp_path / "run"
    (run / "raw").mkdir(parents=True)
    trace_dir = run / "homes/moa/moa-traces"
    trace_dir.mkdir(parents=True)
    (run / "questions.json").write_text("[]")
    manifest = {
        "pairs": [{"question_id": "q1", "sample_index": 0}],
        "arms": {
            "moa": {
                "hermes": {
                    "moa": {
                        "enabled": True,
                        "active_preset": "default",
                        "presets": {
                            "default": {
                                "reference_models": [
                                    {
                                        "provider": "openrouter",
                                        "model": "minimax/minimax-m3",
                                    }
                                ],
                                "aggregator": {
                                    "provider": "openai-codex",
                                    "model": "gpt-5.6-sol",
                                },
                            }
                        },
                    }
                }
            }
        },
    }
    (run / "manifest.json").write_text(json.dumps(manifest))
    answer = {"choices": [{"turns": ["answer"]}]}
    (run / "raw/hermes-moa.jsonl").write_text(json.dumps(answer) + "\n")
    trace = {
        "preset": "default",
        "references": [
            {
                "provider": "openrouter",
                "model": "minimax/minimax-m3",
                "output": "(empty response)",
                "usage": {"input_tokens": 1, "output_tokens": 10_000},
            }
        ],
        "aggregator": {
            "provider": "openai-codex",
            "model": "gpt-5.6-sol",
            "output": "answer",
        },
    }
    (trace_dir / "s.jsonl").write_text(json.dumps(trace) + "\n")

    with pytest.raises(ContractError, match="degraded reference output"):
        score_run(run)
