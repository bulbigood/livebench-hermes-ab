import argparse
import json
import subprocess
from pathlib import Path

import yaml

from livebench_hermes_ab import cli
from livebench_hermes_ab.config import load_config


def test_no_network_fake_hermes_prepare_run_score(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "project"
    upstream = root / "upstream"
    upstream.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=upstream, check=True)
    subprocess.run(["git", "config", "user.email", "fake@example.test"], cwd=upstream, check=True)
    subprocess.run(["git", "config", "user.name", "Fake"], cwd=upstream, check=True)
    (upstream / "fixture").write_text("offline\n")
    subprocess.run(["git", "add", "fixture"], cwd=upstream, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=upstream, check=True)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=upstream, check=True, capture_output=True, text=True
    ).stdout.strip()

    data = root / "data"
    data.mkdir()
    question_id = "offline-exact"
    (data / "questions.jsonl").write_text(
        json.dumps(
            {
                "question_id": question_id,
                "category": "reasoning",
                "task": "exact_match",
                "turns": ["Return exactly: offline-answer"],
                "ground_truth": "offline-answer",
            }
        )
        + "\n"
    )
    source_home = tmp_path / "hermes-home"
    source_home.mkdir()
    (source_home / "auth.json").write_text("{}\n")
    monkeypatch.setenv("HERMES_HOME", str(source_home))

    executable = tmp_path / "fake-hermes"
    executable.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then echo 'Hermes Agent v0.19.1'; exit 0; fi\n"
        "printf '%s\\n' 'offline-answer'\n"
    )
    executable.chmod(0o755)
    config_path = root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "experiment": {
                    "id": "offline-smoke",
                    "upstream_commit": revision,
                    "release": "fixture",
                    "seed": 7,
                    "question_globs": ["data/*.jsonl"],
                },
                "selection": {
                    "scenarios": {
                        "reasoning": [{"id": question_id, "family": "exact_match"}]
                    }
                },
                "generation": {
                    "samples_per_task": 1,
                    "retry": {"max_attempts": 2, "retryable_codes": []},
                },
                "execution": {
                    "mode": "streaming",
                    "workers": 1,
                    "timeout_seconds": 10,
                    "baseline_arm": "base",
                },
                "compatibility": {"hermes": {"profile": "0.19.1"}},
                "arms": {
                    "base": {
                        "credential_env": [],
                        "hermes": {
                            "model": {"provider": "fake", "default": "offline"},
                            "agent": {"reasoning_effort": "none", "disabled_toolsets": []},
                            "moa": {"enabled": False, "save_traces": False},
                        },
                    }
                },
                "scoring": {
                    "implementation": "livebench-objective-ground-truth",
                    "schema_version": 2,
                },
            },
            sort_keys=False,
        )
    )
    run_dir = tmp_path / "run"
    monkeypatch.setattr(cli, "ROOT", root)
    common = {
        "config": config_path,
        "run_dir": run_dir,
        "hermes_executable": executable,
    }
    cli.command_prepare(
        argparse.Namespace(**common, credentials_file=None), load_config(config_path)
    )
    assert cli.command_run(argparse.Namespace(**common))["terminal_cells"] == 1
    scored = cli.command_score(argparse.Namespace(**common))

    assert scored["common_valid_pairs"] == 1
    assert scored["arm_means"] == {"base": 1.0}
    assert (run_dir / "execution.current").is_file()
    assert (run_dir / "scoring.current").is_file()
