from pathlib import Path

import yaml

from livebench_hermes_ab.cli import configure_homes


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
                    "reasoning_effort": "low",
                },
            },
        },
    }
    output = tmp_path / "homes"
    configure_homes(config, source, output)
    assert (output / "base/.env").read_text() == "\n"
    assert (output / "moa/.env").read_text() == "OPENROUTER_API_KEY=allowed\n"
    assert (output / "base/auth.json").is_symlink()
    assert yaml.safe_load((output / "base/config.yaml").read_text())["agent"][
        "reasoning_effort"
    ] == "low"
