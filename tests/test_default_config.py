from copy import deepcopy
from pathlib import Path

import yaml


def test_default_arms_have_expected_models_and_reasoning():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "config.yaml").read_text())

    assert config["experiment"]["id"] == "livebench-hermes-targeted-moa-15x5-v6"
    assert list(config["arms"]) == ["base", "gpt_medium", "moa_minimax", "moa_mimo"]
    assert config["execution"]["baseline_arm"] == "base"
    assert config["execution"]["scheduling"] == "streaming"
    assert config["execution"]["workers"] == "auto"

    base = config["arms"]["base"]["hermes"]
    assert base["model"] == {"provider": "openai-codex", "default": "gpt-5.6-sol"}
    assert base["agent"]["reasoning_effort"] == "low"
    assert base["moa"] == {"enabled": False, "save_traces": False}

    gpt_medium = config["arms"]["gpt_medium"]["hermes"]
    assert gpt_medium["model"] == {"provider": "openai-codex", "default": "gpt-5.6-sol"}
    assert gpt_medium["agent"]["reasoning_effort"] == "medium"
    assert gpt_medium["moa"] == {"enabled": False, "save_traces": False}

    minimax = deepcopy(config["arms"]["moa_minimax"])
    mimo = deepcopy(config["arms"]["moa_mimo"])
    for arm in (minimax, mimo):
        hermes = arm["hermes"]
        preset = hermes["moa"]["presets"]["default"]
        assert "reasoning_effort" not in hermes["agent"]
        assert preset["aggregator"] == {
            "provider": "openai-codex",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
        }
        assert preset["reference_max_tokens"] == 50000

    minimax_reference = minimax["hermes"]["moa"]["presets"]["default"].pop("reference_models")
    mimo_reference = mimo["hermes"]["moa"]["presets"]["default"].pop("reference_models")

    assert minimax == mimo
    assert minimax_reference == [{"provider": "openrouter", "model": "minimax/minimax-m3"}]
    assert mimo_reference == [{"provider": "openrouter", "model": "xiaomi/mimo-v2.5"}]
