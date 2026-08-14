from livebench_hermes_ab.domain import CellId, ValidOutcome
from livebench_hermes_ab.evidence import billing_summary, mechanism_summary
from livebench_hermes_ab.scoring import QuestionEvidence


def _outcome() -> ValidOutcome:
    trace = {
        "preset": "default",
        "references": [
            {
                "provider": "openrouter",
                "model": "ref",
                "output": "CANDIDATE: 42",
                "usage": {"input_tokens": 10, "output_tokens": 2},
                "estimated_cost_usd": 0.01,
                "cost_status": "estimated",
                "generation_id": "gen-ref",
            }
        ],
        "aggregator": {
            "provider": "openai",
            "model": "agg",
            "output": "42",
            "messages": [
                {
                    "role": "user",
                    "content": "<BEGIN_UNTRUSTED_REFERENCE_BLOCKS>x<END_UNTRUSTED_REFERENCE_BLOCKS>",
                }
            ],
            "usage": {"input_tokens": 20, "output_tokens": 1},
            "actual_cost_usd": 0.02,
            "cost_status": "actual",
            "generation_id": "gen-agg",
        },
    }
    return ValidOutcome(
        CellId("critic", "pair", "q", 0),
        {"answer": "42", "moa_traces": [trace]},
        1.0,
    )


def test_billing_summary_groups_calls_and_requires_all_completeness_dimensions() -> None:
    summary = billing_summary((_outcome(),), source="attempts")

    assert summary["complete"] is True
    assert summary["recorded_calls"] == 2
    assert summary["input_tokens"] == 30
    assert summary["output_tokens"] == 3
    assert summary["estimated_cost_usd"] == 0.01
    assert summary["actual_cost_usd"] == 0.02
    assert {row["role"] for row in summary["groups"]} == {"reference", "aggregator"}


def test_mechanism_summary_scores_candidate_and_reports_proxy_bounds() -> None:
    question = QuestionEvidence("math", "exact", {"ground_truth": "42"})
    summary = mechanism_summary(
        (_outcome(),),
        {"q": question},
        {"exact": lambda raw, answer: float(answer == raw["ground_truth"])},
    )

    critic = summary["by_arm"]["critic"]
    assert summary["semantic_claim_annotations_available"] is False
    assert critic["candidate_present"] == 1
    assert critic["candidate_full_correct"] == 1
    assert critic["candidate_exact_adoption"] == 1
    assert critic["useful_candidate_adoption"] == 1
    assert critic["erroneous_candidate_adoption"] == 0
    assert critic["untrusted_wrapper_present"] == 1
