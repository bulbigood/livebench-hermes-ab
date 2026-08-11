from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from .core import (
    ContractError,
    build_command,
    build_prompt,
    canonical_json,
    filter_livebench_snapshot,
    load_jsonl,
    make_pairs,
    select_stratified_complexity,
    sha256_bytes,
    validate_frozen_selection,
    validate_treatment_boundary,
)
from .trace_validation import validate_moa_traces

ROOT = Path(__file__).resolve().parents[2]

DISABLED_TOOLSETS = [
    "web",
    "browser",
    "terminal",
    "file",
    "code_execution",
    "vision",
    "video",
    "image_gen",
    "video_gen",
    "bfl",
    "x_search",
    "tts",
    "stt",
    "skills",
    "todo",
    "memory",
    "context_engine",
    "session_search",
    "clarify",
    "delegation",
    "cronjob",
    "homeassistant",
    "spotify",
    "yuanbao",
    "computer_use",
]


def load_config(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if "experiment" in raw:
        experiment = dict(raw.get("experiment", {}))
        config = {
            "experiment_id": experiment.pop("id"),
            **experiment,
            "selection": raw.get("selection", {}),
            "generation": raw.get("generation", {}),
            "execution": raw.get("execution", {}),
            "arms": raw.get("arms", {}),
        }
        config["concurrency"] = len(config["arms"])
        validate_generic_config(config)
    else:
        config = raw
        validate_treatment_boundary(config)
    return config


def validate_generic_config(config: dict[str, Any]) -> None:
    arms = config.get("arms", {})
    if len(arms) < 2:
        raise ContractError("TOML experiments require at least two arms")
    if config.get("execution", {}).get("workers_per_arm") != 1:
        raise ContractError("execution.workers_per_arm must be exactly 1")
    for name, arm in arms.items():
        if not name.replace("-", "").replace("_", "").isalnum():
            raise ContractError(f"unsafe arm name: {name}")
        hermes = arm.get("hermes")
        if not isinstance(hermes, dict):
            raise ContractError(f"arm {name} requires a hermes table")
        arm_identity(arm)
        credentials = arm.get("credential_env", [])
        if not isinstance(credentials, list) or not all(
            isinstance(key, str) for key in credentials
        ):
            raise ContractError(f"arm {name} credential_env must be a list of names")


def arm_hermes_config(arm: dict[str, Any]) -> dict[str, Any]:
    if "hermes" in arm:
        return arm["hermes"]
    cfg: dict[str, Any] = {
        "model": {"default": arm["model"], "provider": arm["provider"]},
        "agent": {
            "reasoning_effort": str(
                arm.get("reasoning_effort") or arm.get("aggregator", {}).get("reasoning_effort")
            ),
            "disabled_toolsets": DISABLED_TOOLSETS,
        },
        "moa": {
            "enabled": bool(arm["moa_enabled"]),
            "default_preset": "default",
            "active_preset": "default" if arm["moa_enabled"] else "",
            "save_traces": bool(arm["moa_enabled"]),
            "presets": {},
        },
    }
    if arm["moa_enabled"]:
        cfg["moa"]["presets"]["default"] = {
            "enabled": True,
            "degraded_reference_policy": "loud",
            "reference_max_tokens": 10000,
            "max_tokens": 4096,
            "fanout": "every_n:3",
            "reference_models": arm["references"],
            "aggregator": arm["aggregator"],
        }
    return cfg


def arm_identity(arm: dict[str, Any]) -> tuple[str, str, str]:
    hermes = arm_hermes_config(arm)
    try:
        return (
            str(hermes["model"]["provider"]),
            str(hermes["model"]["default"]),
            str(hermes["agent"]["reasoning_effort"]),
        )
    except KeyError as error:
        raise ContractError(f"incomplete Hermes model/agent config: missing {error}") from error


def arm_reference_models(arm: dict[str, Any]) -> list[dict[str, Any]]:
    if "hermes" not in arm:
        return list(arm.get("references") or [])
    moa = arm["hermes"].get("moa", {})
    if not moa.get("enabled"):
        return []
    preset_name = str(moa.get("active_preset") or moa.get("default_preset") or "default")
    preset = moa.get("presets", {}).get(preset_name, {})
    return list(preset.get("reference_models") or [])


def effective_timeout(config: dict[str, Any]) -> int:
    timeout = int(config.get("generation", {}).get("timeout_seconds", 0))
    if timeout <= 0:
        raise ContractError("generation.timeout_seconds must be positive")
    return timeout


def paired_arm_parallelism(config: dict[str, Any]) -> bool:
    execution = config.get("execution", {})
    if execution.get("parallelism") != "paired_arms":
        return False
    workers = execution.get("workers_per_arm")
    if "hermes" in next(iter(config["arms"].values())):
        valid = workers == 1 and int(config.get("concurrency", 0)) == len(config["arms"])
    else:
        valid = workers == {"base": 1, "moa": 1} and int(config.get("concurrency", 0)) == 2
    if not valid:
        raise ContractError("paired_arms requires exactly one worker per configured arm")
    return True


def configure_homes(config: dict[str, Any], source_home: Path, output_root: Path) -> None:
    for arm_name, arm in config["arms"].items():
        home = output_root / arm_name
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
        cfg = arm_hermes_config(arm)
        (home / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=True), encoding="utf-8")
        os.chmod(home / "config.yaml", 0o600)
        auth_source = source_home / "auth.json"
        auth_target = home / "auth.json"
        if not auth_source.is_file():
            raise ContractError(f"credential source missing: {auth_source}")
        if auth_target.exists() or auth_target.is_symlink():
            auth_target.unlink()
        auth_target.symlink_to(auth_source)

        env_sources = [source_home / ".env", Path("/etc/environment")]
        allowed = set(
            arm.get(
                "credential_env",
                ["OPENROUTER_API_KEY"] if arm.get("moa_enabled") else [],
            )
        )
        resolved: dict[str, str] = {}
        for key in allowed:
            if os.environ.get(key):
                resolved[key] = os.environ[key]
        for env_source in env_sources:
            if not env_source.is_file():
                continue
            for line in env_source.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if text.startswith("export "):
                    text = text[7:].lstrip()
                if "=" not in text or text.startswith("#"):
                    continue
                key, value = text.split("=", 1)
                key = key.strip()
                if key in allowed and key not in resolved:
                    resolved[key] = value.strip().strip('"').strip("'")
        if set(resolved) != allowed:
            missing = sorted(allowed - set(resolved))
            raise ContractError(f"required credential keys missing: {missing}")
        filtered = [f"{key}={resolved[key]}" for key in sorted(resolved)]
        (home / ".env").write_text("\n".join(filtered) + "\n", encoding="utf-8")
        os.chmod(home / ".env", 0o600)


def discover_questions(config: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for pattern in config["question_globs"]:
        paths.extend(ROOT.glob(pattern))
    return sorted({path.resolve() for path in paths})


def prepare(config_path: Path, source_home: Path, run_dir: Path) -> dict[str, Any]:
    config = load_config(config_path)
    actual_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT / "upstream",
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if actual_commit != config["upstream_commit"]:
        raise ContractError(
            f"upstream commit drift: expected {config['upstream_commit']}, got {actual_commit}"
        )
    question_paths = discover_questions(config)
    if not question_paths:
        raise ContractError(
            "no LiveBench question.jsonl files found; run upstream/livebench/download_questions.py"
        )
    questions = filter_livebench_snapshot(
        load_jsonl(question_paths),
        str(config["release"]),
        {
            "2024-06-24",
            "2024-07-26",
            "2024-08-31",
            "2024-11-25",
            "2025-04-02",
            "2025-04-25",
            "2025-05-30",
            "2025-11-25",
            "2025-12-23",
            "2026-01-08",
            "2026-06-25",
        },
    )
    if not questions:
        raise ContractError(f"no active questions for LiveBench release {config['release']}")
    if "selection" in config:
        selection = config["selection"]
        requested_ids = [str(value) for value in selection["question_ids"]]
        if len(requested_ids) != len(set(requested_ids)):
            raise ContractError("selection contains duplicate question IDs")
        by_question_id = {str(q["question_id"]): q for q in questions}
        missing = [qid for qid in requested_ids if qid not in by_question_id]
        if missing:
            raise ContractError(f"selected question IDs unavailable: {missing}")
        selected = [by_question_id[qid] for qid in requested_ids]
        validate_frozen_selection(selected, selection)
        samples_per_task = int(config["generation"]["samples_per_task"])
        selection_method = "frozen explicit question IDs; output-blind stratified shortlist"
    else:
        selected = select_stratified_complexity(
            questions,
            [str(category) for category in config["selection_categories"]],
            int(config["seed"]),
        )
        if int(config["sample_size"]) != len(selected):
            raise ContractError("sample_size must equal the number of selection_categories")
        samples_per_task = 1
        selection_method = "one-per-category blind complexity rank"
    execution_arms = list(config.get("execution_arms") or config["arms"])
    selected_pairs = make_pairs(
        selected, int(config["seed"]), samples_per_task, arms=execution_arms
    )

    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    configure_homes(config, source_home, run_dir / "homes")
    sanitized_questions = [{k: v for k, v in q.items() if k != "_source_file"} for q in selected]
    manifest = {
        "experiment_id": config["experiment_id"],
        "upstream_commit": config["upstream_commit"],
        "config_sha256": sha256_bytes(config_path.read_bytes()),
        "question_file_sha256": {str(p): sha256_bytes(p.read_bytes()) for p in question_paths},
        "question_count": len(questions),
        "task_count": len(selected),
        "samples_per_task": samples_per_task,
        "paired_units": len(selected_pairs),
        "expected_cells": len(selected_pairs) * len(execution_arms),
        "expected_model_calls": {
            "by_arm": {
                arm: {
                    "main": len(selected_pairs),
                    "references": len(selected_pairs)
                    * len(arm_reference_models(config["arms"][arm])),
                }
                for arm in execution_arms
            },
            "judge": 0,
            "total": sum(
                len(selected_pairs) * (1 + len(arm_reference_models(config["arms"][arm])))
                for arm in execution_arms
            ),
        },
        "pairs": selected_pairs,
        "questions_sha256": sha256_bytes(canonical_json(sanitized_questions)),
        "home_config_sha256": {
            arm: sha256_bytes((run_dir / "homes" / arm / "config.yaml").read_bytes())
            for arm in config["arms"]
        },
        "selection": {
            "method": selection_method,
            "question_ids": [str(q["question_id"]) for q in selected],
            "category_counts": {
                category: sum(q.get("category") == category for q in selected)
                for category in sorted({str(q.get("category")) for q in selected})
            },
        },
        "execution_contract": {
            "concurrency": int(config["concurrency"]),
            "baseline_arm": config.get("execution", {}).get("baseline_arm", "base"),
            "parallelism": config.get("execution", {}).get("parallelism", "sequential"),
            "workers_per_arm": config.get("execution", {}).get(
                "workers_per_arm", {"base": 1, "moa": 1}
            ),
            "retries": int(config.get("generation", {}).get("retries", 0)),
            "timeout_seconds": int(config.get("generation", {}).get("timeout_seconds", 900)),
            "order": (
                "seeded task/sample order; all arms synchronized per cell"
                if paired_arm_parallelism(config)
                else "seeded shuffle of task/sample units; alternating arm-first order"
            ),
        },
        "arms": config["arms"],
    }
    (run_dir / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    (run_dir / "questions.json").write_bytes(canonical_json(sanitized_questions) + b"\n")
    return manifest


def verify_run_integrity(config_path: Path, run_dir: Path, manifest: dict[str, Any]) -> None:
    if sha256_bytes(config_path.read_bytes()) != manifest["config_sha256"]:
        raise ContractError("experiment config drift after prepare")
    if (
        sha256_bytes((run_dir / "questions.json").read_bytes().rstrip(b"\n"))
        != manifest["questions_sha256"]
    ):
        raise ContractError("selected questions drift after prepare")
    for arm, expected in manifest["home_config_sha256"].items():
        actual = sha256_bytes((run_dir / "homes" / arm / "config.yaml").read_bytes())
        if actual != expected:
            raise ContractError(f"{arm} Hermes config drift after prepare")


def invoke_arm(
    arm_name: str,
    arm: dict[str, Any],
    home: Path,
    question: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    turns: list[str] = []
    started = time.monotonic()
    for _ in question["turns"]:
        prompt = build_prompt(question, turns)
        command = build_command(arm_name, arm, prompt)
        env = subprocess_environment(home)
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            raise RuntimeError(
                f"{arm_name} failed rc={completed.returncode}: {completed.stderr[-2000:]}"
            )
        turns.append(completed.stdout.strip())
    return {
        "turns": turns,
        "total_time_s": round(time.monotonic() - started, 3),
        "stdout_sha256": sha256_bytes("\n".join(turns).encode()),
    }


def subprocess_environment(home: Path) -> dict[str, str]:
    secret_markers = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in secret_markers)
    }
    env["HERMES_HOME"] = str(home)
    return env


def invoke_pair_parallel(
    arms: dict[str, dict[str, Any]],
    homes: dict[str, Path],
    question: dict[str, Any],
    timeout: int,
    invoke=invoke_arm,
) -> dict[str, dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=len(arms), thread_name_prefix="livebench-arm") as executor:
        futures = {
            arm_name: executor.submit(
                invoke, arm_name, arms[arm_name], homes[arm_name], question, timeout
            )
            for arm_name in arms
        }
        return {arm_name: future.result() for arm_name, future in futures.items()}


def run(config_path: Path, source_home: Path, run_dir: Path) -> None:
    config = load_config(config_path)
    manifest = prepare(config_path, source_home, run_dir)
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    by_id = {str(q["question_id"]): q for q in questions}
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True, mode=0o700)
    existing = [path for path in raw_dir.glob("*.jsonl") if path.stat().st_size]
    if existing:
        raise ContractError(
            "run directory already contains answers; use a fresh run directory to preserve pairing"
        )
    for pair in manifest["pairs"]:
        question = by_id[pair["question_id"]]
        verify_run_integrity(config_path, run_dir, manifest)
        if paired_arm_parallelism(config):
            results = invoke_pair_parallel(
                config["arms"],
                {arm: run_dir / "homes" / arm for arm in config["arms"]},
                question,
                effective_timeout(config),
            )
        else:
            results = {
                arm_name: invoke_arm(
                    arm_name,
                    config["arms"][arm_name],
                    run_dir / "homes" / arm_name,
                    question,
                    effective_timeout(config),
                )
                for arm_name in pair["order"]
            }
        for arm_name in pair["order"]:
            result = results[arm_name]
            provider, model, reasoning = arm_identity(config["arms"][arm_name])
            record = {
                "question_id": question["question_id"],
                "answer_id": sha256_bytes(f"{pair['pair_id']}:{arm_name}".encode())[:16],
                "sample_index": pair["sample_index"],
                "model_id": f"hermes-{arm_name}",
                "choices": [{"index": 0, "turns": result["turns"]}],
                "tstamp": time.time(),
                "total_time_s": result["total_time_s"],
                "total_output_tokens": None,
                "total_input_tokens": None,
                "total_cached_tokens": None,
                "cost_usd": None,
                "api_info": {
                    "provider": provider,
                    "api_name": model,
                    "reasoning_effort": reasoning,
                    "pair_id": pair["pair_id"],
                    "sample_index": pair["sample_index"],
                    "response_sha256": result["stdout_sha256"],
                },
            }
            with (raw_dir / f"hermes-{arm_name}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    for arm_name, arm in config["arms"].items():
        if arm_reference_models(arm):
            validate_moa_traces(
                run_dir,
                expected_count=len(manifest["pairs"]),
                arm_name=arm_name,
                hermes_config=arm_hermes_config(arm),
            )


def run_single_arm(config_path: Path, source_home: Path, run_dir: Path, arm_name: str) -> None:
    config = load_config(config_path)
    if arm_name not in config["arms"]:
        raise ContractError(f"unknown arm: {arm_name}")
    manifest = prepare(config_path, source_home, run_dir)
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    by_id = {str(q["question_id"]): q for q in questions}
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True, mode=0o700)
    answer_path = raw_dir / f"hermes-{arm_name}.jsonl"
    if answer_path.exists() and answer_path.stat().st_size:
        raise ContractError(f"run directory already contains {arm_name} answers")
    for pair in manifest["pairs"]:
        verify_run_integrity(config_path, run_dir, manifest)
        question = by_id[pair["question_id"]]
        result = invoke_arm(
            arm_name,
            config["arms"][arm_name],
            run_dir / "homes" / arm_name,
            question,
            effective_timeout(config),
        )
        provider, model, reasoning = arm_identity(config["arms"][arm_name])
        record = {
            "question_id": question["question_id"],
            "answer_id": sha256_bytes(f"{pair['pair_id']}:{arm_name}".encode())[:16],
            "sample_index": pair["sample_index"],
            "model_id": f"hermes-{arm_name}",
            "choices": [{"index": 0, "turns": result["turns"]}],
            "tstamp": time.time(),
            "total_time_s": result["total_time_s"],
            "total_output_tokens": None,
            "total_input_tokens": None,
            "total_cached_tokens": None,
            "cost_usd": None,
            "api_info": {
                "provider": provider,
                "api_name": model,
                "reasoning_effort": reasoning,
                "pair_id": pair["pair_id"],
                "sample_index": pair["sample_index"],
                "response_sha256": result["stdout_sha256"],
            },
        }
        with answer_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    if arm_reference_models(config["arms"][arm_name]):
        validate_moa_traces(
            run_dir,
            expected_count=len(manifest["pairs"]),
            arm_name=arm_name,
            hermes_config=arm_hermes_config(config["arms"][arm_name]),
        )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Multi-arm Hermes Agent runner for LiveBench")
    p.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    p.add_argument("--source-hermes-home", type=Path, default=Path.home() / ".hermes")
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="No-cost validation and manifest creation")
    prep.add_argument("--run-dir", type=Path, default=ROOT / "runs/smoke")
    execute = sub.add_parser("run", help="Execute paid paired model calls")
    execute.add_argument("--run-dir", type=Path, default=ROOT / "runs/smoke")

    execute_arm = sub.add_parser("run-arm", help="Execute a frozen single treatment arm")
    execute_arm.add_argument("--arm", required=True)
    execute_arm.add_argument("--run-dir", type=Path, required=True)

    score = sub.add_parser("score", help="Run pinned deterministic LiveBench scorers")
    score.add_argument("--run-dir", type=Path, default=ROOT / "runs/smoke")
    return p


def main() -> None:
    args = parser().parse_args()
    try:
        if args.command == "prepare":
            manifest = prepare(args.config, args.source_hermes_home, args.run_dir)
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
        elif args.command == "run":
            run(args.config, args.source_hermes_home, args.run_dir)
        elif args.command == "run-arm":
            run_single_arm(args.config, args.source_hermes_home, args.run_dir, args.arm)
        else:
            from .scoring import score_run

            print(json.dumps(score_run(args.run_dir), indent=2, ensure_ascii=False))
    except (ContractError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
