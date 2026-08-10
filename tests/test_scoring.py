from livebench_hermes_ab.scoring import score_standard


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
