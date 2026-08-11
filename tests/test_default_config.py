from copy import deepcopy
from pathlib import Path

import yaml


def test_default_moa_arms_differ_only_by_reference_model():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "config.yaml").read_text())

    assert config["experiment"]["id"] == "livebench-hermes-targeted-moa-15x5-v4"
    assert list(config["arms"]) == ["base", "moa_minimax", "moa_mimo"]
    assert config["execution"]["baseline_arm"] == "base"
    assert config["execution"]["scheduling"] == "streaming"
    assert config["execution"]["workers"] == "auto"

    minimax = deepcopy(config["arms"]["moa_minimax"])
    mimo = deepcopy(config["arms"]["moa_mimo"])

    assert minimax["hermes"]["moa"]["presets"]["default"]["reference_max_tokens"] == 30000
    assert mimo["hermes"]["moa"]["presets"]["default"]["reference_max_tokens"] == 30000

    minimax_reference = minimax["hermes"]["moa"]["presets"]["default"].pop("reference_models")
    mimo_reference = mimo["hermes"]["moa"]["presets"]["default"].pop("reference_models")

    assert minimax == mimo
    assert minimax_reference == [{"provider": "openrouter", "model": "minimax/minimax-m3"}]
    assert mimo_reference == [{"provider": "openrouter", "model": "xiaomi/mimo-v2.5"}]
