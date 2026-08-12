from livebench_hermes_ab.cli import parser


def test_cli_has_only_canonical_commands() -> None:
    commands = parser()._subparsers._group_actions[0].choices
    assert tuple(commands) == ("prepare", "run", "resume", "score")


def test_prepare_has_no_config_field_overrides() -> None:
    prepare = parser()._subparsers._group_actions[0].choices["prepare"]
    option_strings = {option for action in prepare._actions for option in action.option_strings}
    assert "--jobs" not in option_strings
    assert "--samples" not in option_strings
