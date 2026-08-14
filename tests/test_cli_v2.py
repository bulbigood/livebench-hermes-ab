from pathlib import Path

import yaml

from livebench_hermes_ab.cli import _pipeline_config, _workers, parser


def test_pipeline_config_defaults_to_one_sample_without_mutating_source() -> None:
    source = Path("config.yaml")
    config, temporary = _pipeline_config(source, full=False)
    assert config.generation.samples_per_task == 1
    assert temporary is not None
    assert yaml.safe_load(temporary.read_text())["generation"]["samples_per_task"] == 1
    assert yaml.safe_load(source.read_text())["generation"]["samples_per_task"] == 10
    temporary.unlink()

    full, temporary = _pipeline_config(source, full=True)
    assert full.generation.samples_per_task == 10
    assert temporary is None


def test_cli_defaults_to_safe_one_sample_pipeline() -> None:
    args = parser().parse_args([])
    assert args.command is None
    assert args.full is False


def test_full_flag_uses_configured_sample_count() -> None:
    args = parser().parse_args(["--full"])
    assert args.command is None
    assert args.full is True


def test_auto_workers_use_five_per_cpu_with_cap(monkeypatch) -> None:
    monkeypatch.setattr("livebench_hermes_ab.cli.os.cpu_count", lambda: 2)
    assert _workers("auto") == 10
    monkeypatch.setattr("livebench_hermes_ab.cli.os.cpu_count", lambda: 128)
    assert _workers("auto") == 40


def test_cli_has_only_canonical_commands() -> None:
    commands = parser()._subparsers._group_actions[0].choices
    assert tuple(commands) == ("prepare", "run", "resume", "extend", "score")


def test_prepare_has_no_config_field_overrides() -> None:
    prepare = parser()._subparsers._group_actions[0].choices["prepare"]
    option_strings = {option for action in prepare._actions for option in action.option_strings}
    assert "--jobs" not in option_strings
    assert "--samples" not in option_strings
    assert "--credentials-file" in option_strings


def test_credentials_file_is_prepare_only() -> None:
    commands = parser()._subparsers._group_actions[0].choices
    for name in ("run", "resume", "score"):
        option_strings = {
            option for action in commands[name]._actions for option in action.option_strings
        }
        assert "--credentials-file" not in option_strings


def test_extend_requires_new_output_and_target_sample_count() -> None:
    extend = parser()._subparsers._group_actions[0].choices["extend"]
    options = {option for action in extend._actions for option in action.option_strings}
    assert {"--run-dir", "--output-run-dir", "--to-samples", "--credentials-file"} <= options
