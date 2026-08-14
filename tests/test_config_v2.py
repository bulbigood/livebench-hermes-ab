from pathlib import Path

import pytest

from livebench_hermes_ab.config import load_config, parse_config
from livebench_hermes_ab.domain import ConfigError, ExclusionCode


def test_default_config_is_strict_typed_and_ordered() -> None:
    config = load_config(Path("config.yaml"))
    assert tuple(arm.name for arm in config.arms) == (
        "base",
        "moa_mimo",
    )
    assert config.baseline_arm == "base"
    assert config.execution.mode == "streaming"
    assert config.scoring.schema_version == 2
    assert config.generation.retry.retryable_codes == frozenset()
    assert config.experiment_id == "livebench-hermes-production-15x10-v15"
    assert config.generation.samples_per_task == 10
    assert config.compatibility.hermes.mode == "git"
    assert config.compatibility.hermes.repository == (
        "https://github.com/NousResearch/hermes-agent.git"
    )
    assert config.compatibility.hermes.commit == (
        "bfff32ae8c6a9c585431997a6cc3d791b6ec9af5"
    )
    scenarios = [
        item
        for items in config.selection.scenarios.values()
        for item in items
    ]
    assert len(scenarios) == 15
    assert len({item["id"] for item in scenarios}) == 15
    families = {item["family"] for item in scenarios}
    assert families == {
        "paraphrase",
        "math_comp",
        "olympiad",
        "tablejoin",
        "cta",
    }
    for arm in config.arms:
        preset = arm.hermes["moa"].get("presets", {}).get("default")
        if preset is not None:
            assert preset["reference_max_tokens"] == 50_000


def test_unknown_and_legacy_config_fail_closed() -> None:
    with pytest.raises(ConfigError, match="unsupported keys"):
        parse_config({"experiment": {}, "legacy": True})
    with pytest.raises(ConfigError, match="required keys"):
        parse_config({"generation": {"retries": 2}})


def test_hermes_source_supports_exactly_three_exclusive_modes() -> None:
    import copy

    import yaml

    value = yaml.safe_load(Path("config.yaml").read_text())

    release = copy.deepcopy(value)
    release["compatibility"]["hermes"] = {"release": "0.19.1"}
    parsed = parse_config(release).compatibility.hermes
    assert (parsed.mode, parsed.release) == ("release", "0.19.1")

    directory = copy.deepcopy(value)
    directory["compatibility"]["hermes"] = {"directory": "/opt/hermes-agent"}
    parsed = parse_config(directory).compatibility.hermes
    assert (parsed.mode, parsed.directory) == ("directory", "/opt/hermes-agent")

    invalid = copy.deepcopy(value)
    invalid["compatibility"]["hermes"] = {
        "release": "0.19.1",
        "directory": "../hermes-agent",
    }
    with pytest.raises(ConfigError, match="exactly one source mode"):
        parse_config(invalid)

    incomplete_git = copy.deepcopy(value)
    incomplete_git["compatibility"]["hermes"] = {
        "repository": "https://example.test/hermes.git"
    }
    with pytest.raises(ConfigError, match="repository and commit"):
        parse_config(incomplete_git)


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


def test_moa_advisory_prompt_selector_is_strict() -> None:
    import yaml

    value = yaml.safe_load(Path("config.yaml").read_text())
    preset = value["arms"]["moa_mimo"]["hermes"]["moa"]["presets"]["default"]
    preset["advisory_prompt"] = "critic"
    assert parse_config(value).arms[1].hermes["moa"]["presets"]["default"]["advisory_prompt"] == "critic"
    preset["advisory_prompt"] = "invented"
    with pytest.raises(ConfigError, match="advisory_prompt"):
        parse_config(value)


def test_balanced_workers_must_be_explicit_multiple_of_arm_count() -> None:
    import yaml

    value = yaml.safe_load(Path("config.yaml").read_text())
    value["execution"]["mode"] = "balanced_waves"
    value["execution"]["workers"] = 5
    with pytest.raises(ConfigError, match="multiple of the 2 arms"):
        parse_config(value)

    value["execution"]["workers"] = 4
    assert parse_config(value).execution.workers == 4

    value["execution"]["workers"] = "auto"
    with pytest.raises(ConfigError, match="requires an explicit worker count"):
        parse_config(value)
