from livebench_hermes_ab.scoring import score_standard, summary_status


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
