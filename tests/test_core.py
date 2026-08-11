import pytest

from livebench_hermes_ab.core import (
    ContractError,
    build_command,
    build_prompt,
    filter_livebench_snapshot,
    make_pairs,
    resolve_explicit_scenarios,
    validate_frozen_selection,
    validate_treatment_boundary,
)


def config():
    return {
        "arms": {
            "base": {
                "provider": "openai-codex",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "medium",
                "moa_enabled": False,
            },
            "moa": {
                "provider": "moa",
                "model": "default",
                "reasoning_effort": "medium",
                "moa_enabled": True,
                "preset": "default",
                "aggregator": {
                    "provider": "openai-codex",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                },
                "references": [{"provider": "openrouter", "model": "minimax/minimax-m3"}],
            },
        }
    }


def test_treatment_boundary_accepts_only_reference_context_difference():
    validate_treatment_boundary(config())


def test_prompt_is_arm_independent_and_preserves_system_and_turns():
    q = {"question_id": "q1", "system_prompt": "Be exact.", "turns": ["First", "Second"]}
    assert build_prompt(q, prior_answers=[]) == "Be exact.\n\nFirst"
    assert build_prompt(q, prior_answers=["A"]) == (
        "Be exact.\n\nFirst\n\nAssistant's previous response:\nA\n\nSecond"
    )


def test_commands_pin_provider_model_and_disable_tools():
    base = build_command("base", config()["arms"]["base"], "hello")
    moa = build_command("moa", config()["arms"]["moa"], "hello")
    assert base[-4:] == ["--provider", "openai-codex", "--model", "gpt-5.6-sol"]
    assert moa[-4:] == ["--provider", "moa", "--model", "default"]
    assert "--toolsets" not in base
    assert "--ignore-rules" in base
    assert "--safe-mode" not in base


def test_pair_order_is_balanced_and_deterministic():
    questions = [{"question_id": f"q{i}"} for i in range(5)]
    one = make_pairs(questions, seed=7)
    two = make_pairs(questions, seed=7)
    assert one == two
    assert [p["order"] for p in one] == [
        ["base", "moa"],
        ["moa", "base"],
        ["base", "moa"],
        ["moa", "base"],
        ["base", "moa"],
    ]
    assert len({p["pair_id"] for p in one}) == 5


def test_pair_matrix_has_five_samples_per_task_and_unique_cells():
    questions = [{"question_id": "q1"}, {"question_id": "q2"}]
    pairs = make_pairs(questions, seed=7, samples_per_task=5)
    assert len(pairs) == 10
    assert {(p["question_id"], p["sample_index"]) for p in pairs} == {
        (qid, sample) for qid in ("q1", "q2") for sample in range(5)
    }
    assert len({p["pair_id"] for p in pairs}) == 10


def test_snapshot_filter_matches_livebench_removal_cutoff():
    rows = [
        {
            "question_id": "keep",
            "livebench_release_date": "2024-06-24",
            "livebench_removal_date": "",
        },
        {
            "question_id": "removed",
            "livebench_release_date": "2024-06-24",
            "livebench_removal_date": "2025-01-01",
        },
        {
            "question_id": "unknown",
            "livebench_release_date": "2099-01-01",
            "livebench_removal_date": "",
        },
    ]
    got = filter_livebench_snapshot(rows, "2026-06-25", {"2024-06-24"})
    assert [q["question_id"] for q in got] == ["keep"]


def test_frozen_selection_enforces_exact_category_counts():
    selected = [
        {"category": "reasoning"},
        {"category": "reasoning"},
        {"category": "data_analysis"},
    ]
    selection = {
        "new_task_count": 3,
        "category_task_counts": {"reasoning": 2, "data_analysis": 1},
    }
    validate_frozen_selection(selected, selection)
    selection["category_task_counts"] = {"reasoning": 1, "data_analysis": 2}
    with pytest.raises(ContractError, match="category task cardinality mismatch"):
        validate_frozen_selection(selected, selection)


def test_frozen_selection_enforces_exact_task_family_counts():
    selected = [
        {"category": "reasoning", "task": "zebra_puzzle"},
        {"category": "reasoning", "task": "spatial"},
    ]
    selection = {
        "new_task_count": 2,
        "category_task_counts": {"reasoning": 2},
        "task_family_counts": {"reasoning": {"zebra_puzzle": 1, "spatial": 1}},
    }
    validate_frozen_selection(selected, selection)
    selection["task_family_counts"] = {"reasoning": {"zebra_puzzle": 2}}
    with pytest.raises(ContractError, match="task family cardinality mismatch"):
        validate_frozen_selection(selected, selection)


def test_grouped_scenarios_resolve_in_config_order_with_metadata():
    questions = [
        {"question_id": "r1", "category": "reasoning", "task": "spatial"},
        {"question_id": "d1", "category": "data_analysis", "task": "tablejoin"},
    ]
    selected, resolved = resolve_explicit_scenarios(
        questions,
        {
            "scenarios": {
                "data_analysis": [
                    {
                        "id": "d1",
                        "family": "tablejoin",
                        "source_url": "https://example.test/d1",
                    }
                ],
                "reasoning": [{"id": "r1", "family": "spatial", "note": "hard"}],
            }
        },
    )

    assert [row["question_id"] for row in selected] == ["d1", "r1"]
    assert resolved == [
        {
            "id": "d1",
            "category": "data_analysis",
            "family": "tablejoin",
            "source_url": "https://example.test/d1",
        },
        {"id": "r1", "category": "reasoning", "family": "spatial", "note": "hard"},
    ]


@pytest.mark.parametrize(
    ("scenarios", "message"),
    [
        (
            {"data_analysis": [{"id": "r1", "family": "spatial"}]},
            "category mismatch",
        ),
        (
            {"reasoning": [{"id": "r1", "family": "zebra_puzzle"}]},
            "family mismatch",
        ),
        (
            {"reasoning": [{"id": "r1", "family": "spatial", "source_url": "not-a-url"}]},
            "must be an HTTP",
        ),
        (
            {
                "reasoning": [{"id": "r1", "family": "spatial"}],
                "data_analysis": [{"id": "r1", "family": "spatial"}],
            },
            "duplicate scenario IDs",
        ),
        (
            {"reasoning": [{"id": "missing", "family": "spatial"}]},
            "scenario IDs unavailable",
        ),
    ],
)
def test_grouped_scenarios_fail_closed(scenarios, message):
    questions = [{"question_id": "r1", "category": "reasoning", "task": "spatial"}]
    with pytest.raises(ContractError, match=message):
        resolve_explicit_scenarios(questions, {"scenarios": scenarios})


def test_selection_rejects_ambiguous_flat_and_grouped_scenarios():
    with pytest.raises(ContractError, match="exactly one"):
        resolve_explicit_scenarios(
            [{"question_id": "r1", "category": "reasoning", "task": "spatial"}],
            {
                "question_ids": ["r1"],
                "scenarios": {"reasoning": [{"id": "r1", "family": "spatial"}]},
            },
        )
