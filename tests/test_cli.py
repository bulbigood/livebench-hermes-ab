import threading
import time
from pathlib import Path

import pytest
import yaml

from livebench_hermes_ab.cli import (
    arm_identity,
    configure_homes,
    effective_timeout,
    invoke_pair_parallel,
    load_config,
    paired_arm_parallelism,
    subprocess_environment,
)
from livebench_hermes_ab.core import ContractError


def test_timeout_comes_from_frozen_generation_contract():
    assert effective_timeout({"generation": {"timeout_seconds": 1800}}) == 1800


def test_configure_homes_minimizes_credentials(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "auth.json").write_text("{}")
    (source / ".env").write_text(
        "OPENROUTER_API_KEY=allowed\nTELEGRAM_BOT_TOKEN=forbidden\nGITHUB_TOKEN=forbidden\n"
    )
    config = {
        "max_tokens": 4096,
        "arms": {
            "base": {
                "model": "gpt-5.6-sol",
                "provider": "openai-codex",
                "reasoning_effort": "medium",
                "moa_enabled": False,
            },
            "moa": {
                "model": "default",
                "provider": "moa",
                "moa_enabled": True,
                "references": [{"provider": "openrouter", "model": "minimax/minimax-m3"}],
                "aggregator": {
                    "provider": "openai-codex",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                },
            },
        },
    }
    output = tmp_path / "homes"
    configure_homes(config, source, output)
    assert (output / "base/.env").read_text() == "\n"
    assert (output / "moa/.env").read_text() == "OPENROUTER_API_KEY=allowed\n"
    assert (output / "base/auth.json").is_symlink()
    assert (
        yaml.safe_load((output / "base/config.yaml").read_text())["agent"]["reasoning_effort"]
        == "medium"
    )
    disabled = yaml.safe_load((output / "base/config.yaml").read_text())["agent"][
        "disabled_toolsets"
    ]
    assert "terminal" in disabled and "web" in disabled and "memory" in disabled


def test_pair_invocation_runs_one_worker_per_arm_concurrently(tmp_path: Path):
    barrier = threading.Barrier(2)
    active = {"base": 0, "moa": 0}
    peak = {"base": 0, "moa": 0}
    lock = threading.Lock()

    def fake_invoke(arm_name, arm, home, question, timeout):
        with lock:
            active[arm_name] += 1
            peak[arm_name] = max(peak[arm_name], active[arm_name])
        barrier.wait(timeout=1)
        time.sleep(0.01)
        with lock:
            active[arm_name] -= 1
        return {"turns": [arm_name], "total_time_s": 0.01, "stdout_sha256": arm_name}

    result = invoke_pair_parallel(
        arms={"base": {}, "moa": {}},
        homes={"base": tmp_path / "base", "moa": tmp_path / "moa"},
        question={"question_id": "q1", "turns": ["prompt"]},
        timeout=30,
        invoke=fake_invoke,
    )

    assert set(result) == {"base", "moa"}
    assert peak == {"base": 1, "moa": 1}


def test_paired_arm_contract_rejects_more_than_one_worker_per_arm():
    config = {
        "arms": {"base": {}, "moa": {}},
        "concurrency": 3,
        "execution": {
            "parallelism": "paired_arms",
            "workers_per_arm": {"base": 1, "moa": 2},
        },
    }
    with pytest.raises(ContractError, match="paired_arms requires"):
        paired_arm_parallelism(config)


def test_yaml_arms_write_hermes_config_verbatim(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
experiment:
  id: example
  upstream_commit: abc
  release: '2026-06-25'
  seed: 1
  question_globs: [data/*.jsonl]
generation: {samples_per_task: 1, timeout_seconds: 30}
execution: {parallelism: paired_arms, workers_per_arm: 1}
arms:
  control:
    credential_env: []
    hermes:
      model: {provider: openai-codex, default: gpt-5.6-sol}
      agent: {reasoning_effort: low, disabled_toolsets: [terminal]}
  treatment:
    credential_env: [OPENROUTER_API_KEY]
    hermes:
      model: {provider: moa, default: research}
      agent: {reasoning_effort: medium}
      moa:
        enabled: true
        active_preset: research
        save_traces: true
        presets:
          research:
            enabled: true
            degraded_reference_policy: loud
            reference_models:
              - {provider: openrouter, model: minimax/minimax-m3}
            aggregator: {provider: openai-codex, model: gpt-5.6-sol, reasoning_effort: medium}
"""
    )
    source = tmp_path / "source"
    source.mkdir()
    (source / "auth.json").write_text("{}")
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")

    config = load_config(config_path)
    configure_homes(config, source, tmp_path / "homes")

    assert (
        yaml.safe_load((tmp_path / "homes/control/config.yaml").read_text())
        == config["arms"]["control"]["hermes"]
    )
    assert (
        yaml.safe_load((tmp_path / "homes/treatment/config.yaml").read_text())
        == config["arms"]["treatment"]["hermes"]
    )
    assert (tmp_path / "homes/control/.env").read_text() == "\n"
    assert (tmp_path / "homes/treatment/.env").read_text() == "OPENROUTER_API_KEY=secret\n"
    assert arm_identity(config["arms"]["treatment"]) == (
        "moa",
        "research",
        "medium",
    )


def test_subprocess_environment_does_not_inherit_parent_secrets(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-leak")
    monkeypatch.setenv("GH_TOKEN", "must-not-leak")
    monkeypatch.setenv("ORDINARY_SETTING", "kept")
    env = subprocess_environment(tmp_path / "arm-home")
    assert "OPENROUTER_API_KEY" not in env
    assert "GH_TOKEN" not in env
    assert env["ORDINARY_SETTING"] == "kept"
    assert env["HERMES_HOME"] == str(tmp_path / "arm-home")
