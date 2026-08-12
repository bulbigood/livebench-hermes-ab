from pathlib import Path

import pytest

from livebench_hermes_ab.config import load_config, parse_config
from livebench_hermes_ab.domain import ConfigError, ExclusionCode


def test_default_config_is_strict_typed_and_ordered() -> None:
    config = load_config(Path("config.yaml"))
    assert tuple(arm.name for arm in config.arms) == (
        "base",
        "gpt_medium",
        "moa_minimax",
        "moa_mimo",
    )
    assert config.baseline_arm == "base"
    assert config.execution.mode == "streaming"
    assert config.scoring.schema_version == 2
    assert config.generation.retry.retryable_codes == frozenset()
    assert config.experiment_id == "livebench-hermes-targeted-moa-15x5-v7"
    reasoning_ids = {item["id"] for item in config.selection.scenarios["reasoning"]}
    assert {
        "20d48b97e524cd64f82b0e4fb3c597a37bae1d9357e9b2c93aad96b4c70e098e",
        "b1b1678a4f290c8ab2b85f957a0cdbba93ef0c97d1e7ab4663e46e92ebac70e8",
    } <= reasoning_ids
    assert (
        not {
            "6bd178380f1808eadda3b1565ac385a0ed891cb438a611a8142e9002ac35bbe4",
            "c29eb6b3c9fd3f67fba90afc62b89640ba6b6aa5f74bb2efd8d5650af6b78ff6",
        }
        & reasoning_ids
    )
    for arm in config.arms:
        preset = arm.hermes["moa"].get("presets", {}).get("default")
        if preset is not None:
            assert preset["reference_max_tokens"] == 50_000


def test_unknown_and_legacy_config_fail_closed() -> None:
    with pytest.raises(ConfigError, match="unsupported keys"):
        parse_config({"experiment": {}, "legacy": True})
    with pytest.raises(ConfigError, match="required keys"):
        parse_config({"generation": {"retries": 2}})


def test_retry_codes_are_enum_values() -> None:
    config = load_config(Path("config.yaml"))
    assert ExclusionCode.CELL_TIMEOUT not in config.generation.retry.retryable_codes


def test_scoring_precision_defaults_and_validation() -> None:
    import yaml

    value = yaml.safe_load(Path("config.yaml").read_text())
    config = parse_config(value)
    assert config.scoring.confidence_level == 0.95
    assert config.scoring.target_margin_of_error == 0.05

    value["scoring"]["confidence_level"] = 0.9
    value["scoring"]["target_margin_of_error"] = 0.1
    config = parse_config(value)
    assert config.scoring.confidence_level == 0.9
    assert config.scoring.target_margin_of_error == 0.1

    value["scoring"]["confidence_level"] = 1.0
    with pytest.raises(ConfigError, match="confidence_level"):
        parse_config(value)


def test_unknown_nested_arm_key_fails_closed() -> None:
    import yaml

    value = yaml.safe_load(Path("config.yaml").read_text())
    value["arms"]["base"]["hermes"]["model"]["legacy_model"] = "ignored"
    with pytest.raises(ConfigError, match="unsupported keys"):
        parse_config(value)


def test_balanced_workers_must_be_explicit_multiple_of_arm_count() -> None:
    import yaml

    value = yaml.safe_load(Path("config.yaml").read_text())
    value["execution"]["mode"] = "balanced_waves"
    value["execution"]["workers"] = 7
    with pytest.raises(ConfigError, match="multiple of the 4 arms"):
        parse_config(value)

    value["execution"]["workers"] = 8
    assert parse_config(value).execution.workers == 8

    value["execution"]["workers"] = "auto"
    with pytest.raises(ConfigError, match="requires an explicit worker count"):
        parse_config(value)
