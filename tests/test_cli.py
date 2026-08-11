import json
import threading
import time
from pathlib import Path

import pytest
import yaml

from livebench_hermes_ab.cli import (
    arm_identity,
    configure_homes,
    effective_timeout,
    invoke_arm,
    invoke_pair_parallel,
    load_config,
    paired_arm_parallelism,
    parse_hermes_version,
    prepare_cell_home,
    probe_hermes_compatibility,
    resolve_hermes_executable,
    resolve_worker_count,
    run,
    schedule_cells,
    subprocess_environment,
    validate_hermes_arm_schema,
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
    assert (
        yaml.safe_load((output / "moa/config.yaml").read_text())["moa"]["presets"]["default"][
            "reference_max_tokens"
        ]
        == 50000
    )
    disabled = yaml.safe_load((output / "base/config.yaml").read_text())["agent"][
        "disabled_toolsets"
    ]
    assert "terminal" in disabled and "web" in disabled and "memory" in disabled


@pytest.mark.parametrize(
    ("cpu_count", "expected"),
    [(None, 4), (0, 4), (-2, 4), (1, 4), (2, 8), (8, 32), (16, 32)],
)
def test_default_worker_count_is_four_per_cpu_capped_at_32(cpu_count, expected):
    assert resolve_worker_count(None, cpu_count=cpu_count) == expected


@pytest.mark.parametrize("workers", [0, -1, 33, 1.5, "eight", True])
def test_explicit_worker_count_is_fail_closed(workers):
    with pytest.raises(ContractError, match="workers"):
        resolve_worker_count(workers, cpu_count=2)


@pytest.mark.parametrize("workers", [1, 8, 32])
def test_explicit_worker_count_accepts_one_through_32(workers):
    assert resolve_worker_count(workers, cpu_count=2) == workers


def test_streaming_schedule_is_default_and_preserves_deterministic_coverage():
    pairs = [{"pair_id": f"p{index}", "sample_index": index} for index in range(4)]
    arms = ("base", "minimax", "mimo")

    waves = schedule_cells(pairs, arms, scheduling="streaming", workers=8)

    assert len(waves) == 1
    assert {(cell["pair_id"], cell["arm_name"]) for cell in waves[0]} == {
        (pair["pair_id"], arm) for pair in pairs for arm in arms
    }
    assert waves == schedule_cells(pairs, arms, scheduling="streaming", workers=8)


def test_balanced_schedule_uses_complete_arm_groups_and_effective_multiple():
    pairs = [{"pair_id": f"p{index}", "sample_index": index} for index in range(5)]
    arms = ("base", "minimax", "mimo")

    waves = schedule_cells(pairs, arms, scheduling="balanced_waves", workers=8)

    assert [len(wave) for wave in waves] == [6, 6, 3]
    for wave in waves:
        pair_ids = {cell["pair_id"] for cell in wave}
        for pair_id in pair_ids:
            assert {cell["arm_name"] for cell in wave if cell["pair_id"] == pair_id} == set(arms)


def test_balanced_schedule_rejects_fewer_workers_than_arms():
    with pytest.raises(ContractError, match="at least the number of arms"):
        schedule_cells(
            [{"pair_id": "p0", "sample_index": 0}],
            ("base", "minimax", "mimo"),
            scheduling="balanced_waves",
            workers=2,
        )


def test_cell_homes_are_isolated_from_template_and_each_other(tmp_path: Path):
    template = tmp_path / "homes/base"
    template.mkdir(parents=True)
    (template / "config.yaml").write_text("model: {}\n")
    (template / ".env").write_text("SAFE=value\n")
    stale = template / "moa-traces"
    stale.mkdir()
    (stale / "probe.jsonl").write_text("stale\n")

    first = prepare_cell_home(tmp_path, "base", "pair-1")
    second = prepare_cell_home(tmp_path, "base", "pair-2")

    assert first != second
    assert (first / "config.yaml").read_text() == "model: {}\n"
    assert not (first / "moa-traces").exists()
    (first / "session.db").write_text("first")
    assert not (second / "session.db").exists()
    assert not (template / "session.db").exists()


def test_streaming_run_uses_resolved_workers_and_unique_cell_homes(tmp_path: Path, monkeypatch):
    arm_names = ("base", "minimax", "mimo")
    pairs = [
        {"pair_id": f"pair-{index}", "question_id": f"q{index}", "sample_index": 0}
        for index in range(2)
    ]
    config = {
        "arms": {
            name: {
                "hermes": {
                    "model": {"provider": "test", "default": f"model-{name}"},
                    "agent": {"reasoning_effort": "medium"},
                    "moa": {"enabled": False},
                }
            }
            for name in arm_names
        },
        "execution": {"scheduling": "streaming", "workers": 6},
        "generation": {"timeout_seconds": 30},
    }
    run_dir = tmp_path / "run"
    active = 0
    peak = 0
    homes = set()
    barrier = threading.Barrier(6)
    lock = threading.Lock()

    def fake_prepare(*args, **kwargs):
        for arm_name in arm_names:
            home = run_dir / "homes" / arm_name
            home.mkdir(parents=True)
            (home / "config.yaml").write_text("moa: {enabled: false}\n")
        (run_dir / "questions.json").write_text(
            json.dumps([{"question_id": f"q{index}", "turns": ["prompt"]} for index in range(2)])
        )
        return {
            "pairs": pairs,
            "execution_contract": {
                "scheduling": "streaming",
                "requested_workers": 6,
                "effective_workers": 6,
                "timing_comparable": False,
            },
        }

    def fake_invoke(arm_name, arm, home, question, timeout, *, executable):
        nonlocal active, peak
        with lock:
            assert home not in homes
            homes.add(home)
            active += 1
            peak = max(peak, active)
        barrier.wait(timeout=1)
        with lock:
            active -= 1
        return {"turns": [arm_name], "total_time_s": 0.01, "stdout_sha256": arm_name}

    monkeypatch.setattr("livebench_hermes_ab.cli.load_config", lambda path: config)
    monkeypatch.setattr(
        "livebench_hermes_ab.cli.resolve_hermes_executable", lambda value: "/fake/hermes"
    )
    monkeypatch.setattr("livebench_hermes_ab.cli.prepare", fake_prepare)
    monkeypatch.setattr("livebench_hermes_ab.cli.verify_run_integrity", lambda *args: None)
    monkeypatch.setattr("livebench_hermes_ab.cli.invoke_arm", fake_invoke)

    run(tmp_path / "config.yaml", tmp_path / "source", run_dir)

    assert peak == 6
    assert len(homes) == 6
    for arm_name in arm_names:
        rows = (run_dir / "raw" / f"hermes-{arm_name}.jsonl").read_text().splitlines()
        assert len(rows) == 2


def test_wave_invocation_runs_one_worker_per_arm_concurrently(tmp_path: Path):
    arm_names = ("base", "moa_minimax", "moa_mimo")
    barrier = threading.Barrier(len(arm_names))
    active = dict.fromkeys(arm_names, 0)
    peak = dict.fromkeys(arm_names, 0)
    lock = threading.Lock()

    def fake_invoke(arm_name, arm, home, question, timeout, *, executable):
        assert executable == "/project/hermes"
        with lock:
            active[arm_name] += 1
            peak[arm_name] = max(peak[arm_name], active[arm_name])
        barrier.wait(timeout=1)
        time.sleep(0.01)
        with lock:
            active[arm_name] -= 1
        return {"turns": [arm_name], "total_time_s": 0.01, "stdout_sha256": arm_name}

    result = invoke_pair_parallel(
        arms={arm_name: {} for arm_name in arm_names},
        homes={arm_name: tmp_path / arm_name for arm_name in arm_names},
        question={"question_id": "q1", "turns": ["prompt"]},
        timeout=30,
        executable="/project/hermes",
        invoke=fake_invoke,
    )

    assert set(result) == set(arm_names)
    assert peak == dict.fromkeys(arm_names, 1)


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
compatibility:
  hermes: {profile: '0.19.1'}
arms:
  control:
    credential_env: []
    hermes:
      model: {provider: openai-codex, default: gpt-5.6-sol}
      agent: {reasoning_effort: low, disabled_toolsets: [terminal]}
      moa: {enabled: false, save_traces: false}
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


def test_parse_hermes_version_from_real_cli_shape():
    assert (
        parse_hermes_version(
            "Hermes Agent v0.19.1 (2026.7.30) · upstream 863e3131 · local fed098bb\n"
        )
        == "0.19.1"
    )


def test_explicit_hermes_executable_wins_over_path(tmp_path: Path, monkeypatch):
    explicit = tmp_path / "project-hermes"
    explicit.write_text("#!/bin/sh\n")
    explicit.chmod(0o755)
    path_binary = tmp_path / "hermes"
    path_binary.write_text("#!/bin/sh\n")
    path_binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert resolve_hermes_executable(explicit) == str(explicit.resolve())


def test_hermes_executable_environment_override(tmp_path: Path, monkeypatch):
    selected = tmp_path / "environment-hermes"
    selected.write_text("#!/bin/sh\n")
    selected.chmod(0o755)
    monkeypatch.setenv("HERMES_EXECUTABLE", str(selected))
    monkeypatch.setenv("PATH", "")

    assert resolve_hermes_executable() == str(selected.resolve())


def test_missing_explicit_hermes_executable_fails_without_path_fallback(
    tmp_path: Path, monkeypatch
):
    path_binary = tmp_path / "hermes"
    path_binary.write_text("#!/bin/sh\n")
    path_binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(ContractError, match="explicit Hermes executable"):
        resolve_hermes_executable(tmp_path / "missing-hermes")


def test_invoke_arm_uses_selected_hermes_executable(tmp_path: Path, monkeypatch):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return type(
            "Result",
            (),
            {"returncode": 0, "stdout": "answer\n", "stderr": ""},
        )()

    monkeypatch.setattr("livebench_hermes_ab.cli.subprocess.run", fake_run)
    result = invoke_arm(
        "control",
        {
            "hermes": {
                "model": {"provider": "openai-codex", "default": "gpt-test"},
                "agent": {"reasoning_effort": "medium"},
                "moa": {"enabled": False},
            }
        },
        tmp_path,
        {"question_id": "q1", "turns": ["prompt"]},
        30,
        executable="/project/hermes",
    )

    assert commands[0][0] == "/project/hermes"
    assert result["turns"] == ["answer"]


def test_hermes_schema_rejects_unknown_treatment_key():
    arm = {
        "hermes": {
            "model": {
                "provider": "openai-codex",
                "default": "gpt-5.6-sol",
                "reasoning_efford": "medium",
            },
            "agent": {"reasoning_effort": "medium"},
            "moa": {"enabled": False, "save_traces": False},
        }
    }
    with pytest.raises(ContractError, match="arm control.*model.*reasoning_efford"):
        validate_hermes_arm_schema("control", arm, "0.19.1")


def test_hermes_schema_rejects_invalid_reasoning_type():
    arm = {
        "hermes": {
            "model": {"provider": "openai-codex", "default": "gpt-5.6-sol"},
            "agent": {"reasoning_effort": ["medium"]},
            "moa": {"enabled": False, "save_traces": False},
        }
    }
    with pytest.raises(ContractError, match="arm control.*reasoning_effort"):
        validate_hermes_arm_schema("control", arm, "0.19.1")


def test_hermes_schema_rejects_inline_credential_without_echoing_value():
    leaked_value = "fixture-openrouter-value-must-not-appear"
    arm = {
        "hermes": {
            "model": {
                "provider": "openrouter",
                "default": "example/model",
                "api_key": leaked_value,
            },
            "agent": {"reasoning_effort": "medium"},
            "moa": {"enabled": False, "save_traces": False},
        }
    }
    with pytest.raises(ContractError) as caught:
        validate_hermes_arm_schema("control", arm, "0.19.1")
    message = str(caught.value)
    assert "inline credential" in message
    assert "model.api_key" in message
    assert leaked_value not in message


def test_hermes_probe_warns_and_skips_profile_probes_on_version_mismatch(tmp_path: Path):
    config = {
        "compatibility": {"hermes": {"profile": "0.19.1"}},
        "arms": {
            "control": {
                "hermes": {
                    "model": {"provider": "openai-codex", "default": "gpt-5.6-sol"},
                    "agent": {"reasoning_effort": "medium"},
                    "moa": {"enabled": False},
                }
            }
        },
    }
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        assert command == ["/fake/hermes", "--version"]
        return type(
            "Result",
            (),
            {"returncode": 0, "stdout": "Hermes Agent v0.20.0 (test)\n", "stderr": ""},
        )()

    report = probe_hermes_compatibility(
        config,
        {"control": tmp_path / "control"},
        executable="/fake/hermes",
        runner=fake_run,
    )

    assert commands == [["/fake/hermes", "--version"]]
    assert report["status"] == "unverified-version"
    assert report["profile"] == "0.19.1"
    assert report["version"] == "0.20.0"
    assert report["warning_codes"] == ["HERMES_VERSION_MISMATCH"]
    assert "model calls may proceed" in report["warnings"][0]
    assert report["arms"] == {}


def test_hermes_probe_reports_arm_config_failure(tmp_path: Path):
    home = tmp_path / "control"
    home.mkdir()
    config_path = home / "config.yaml"
    config_path.write_text("model: {}\n")
    config = {
        "compatibility": {"hermes": {"profile": "0.19.1"}},
        "arms": {
            "control": {
                "hermes": {
                    "model": {"provider": "openai-codex", "default": "gpt-5.6-sol"},
                    "agent": {"reasoning_effort": "medium"},
                    "moa": {"enabled": False, "save_traces": False},
                }
            }
        },
    }

    def fake_run(command, **kwargs):
        if command[-1] == "--version":
            return type(
                "Result",
                (),
                {"returncode": 0, "stdout": "Hermes Agent v0.19.1 (test)\n", "stderr": ""},
            )()
        return type(
            "Result",
            (),
            {"returncode": 2, "stdout": "", "stderr": "unsupported model.default"},
        )()

    with pytest.raises(ContractError) as caught:
        probe_hermes_compatibility(
            config,
            {"control": home},
            executable="/fake/hermes",
            runner=fake_run,
        )
    message = str(caught.value)
    assert "arm 'control'" in message
    assert "Hermes version: 0.19.1" in message
    assert str(config_path) in message
    assert "unsupported model.default" in message


def test_hermes_probe_records_offline_evidence_for_each_arm(tmp_path: Path):
    arms = {
        name: {
            "hermes": {
                "model": {"provider": "openai-codex", "default": f"model-{name}"},
                "agent": {"reasoning_effort": "medium", "disabled_toolsets": ["terminal"]},
                "moa": {"enabled": False, "save_traces": False},
            }
        }
        for name in ("control", "candidate")
    }
    homes = {}
    for name, arm in arms.items():
        home = tmp_path / name
        home.mkdir()
        (home / "config.yaml").write_text(yaml.safe_dump(arm["hermes"]))
        homes[name] = home
    config = {
        "compatibility": {"hermes": {"profile": "0.19.1"}},
        "arms": arms,
    }

    def fake_run(command, **kwargs):
        if command[-1] == "--version":
            stdout = "Hermes Agent v0.19.1 (test)\n"
        elif command[-2:] == ["config", "check"]:
            stdout = "Configuration OK\n"
        elif command[1:3] == ["config", "get"]:
            key = command[3]
            home_name = Path(kwargs["env"]["HERMES_HOME"]).name
            values = {
                "model.provider": "openai-codex",
                "model.default": f"model-{home_name}",
                "agent.reasoning_effort": "medium",
                "moa.enabled": False,
            }
            stdout = json.dumps(values[key]) + "\n"
        elif command[-2:] == ["prompt-size", "--json"]:
            stdout = '{"tool_schemas": {"count": 0}, "total_tokens": 123}\n'
        else:
            raise AssertionError(command)
        return type("Result", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()

    report = probe_hermes_compatibility(
        config,
        homes,
        executable="/fake/hermes",
        runner=fake_run,
    )
    assert report["status"] == "verified"
    assert report["version"] == "0.19.1"
    assert report["profile"] == "0.19.1"
    assert set(report["arms"]) == {"control", "candidate"}
    assert report["arms"]["control"]["config_check"] == "passed"
    assert report["arms"]["candidate"]["effective"]["model.default"] == "model-candidate"
