from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
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
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_treatment_boundary(config)
    return config


def effective_timeout(config: dict[str, Any]) -> int:
    timeout = int(config.get("generation", {}).get("timeout_seconds", 0))
    if timeout <= 0:
        raise ContractError("generation.timeout_seconds must be positive")
    return timeout


def configure_homes(config: dict[str, Any], source_home: Path, output_root: Path) -> None:
    for arm_name, arm in config["arms"].items():
        home = output_root / arm_name
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
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
        if arm_name == "moa":
            cfg["moa"]["presets"]["default"] = {
                "enabled": True,
                "degraded_reference_policy": "loud",
                "reference_max_tokens": 10000,
                "max_tokens": int(config.get("max_tokens", 4096)),
                "fanout": "every_n:3",
                "reference_models": arm["references"],
                "aggregator": arm["aggregator"],
            }
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
        allowed = {"OPENROUTER_API_KEY"} if arm_name == "moa" else set()
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
        if len(selected) != int(selection["new_task_count"]):
            raise ContractError("new_task_count does not match frozen question IDs")
        math_count = sum(q.get("category") == "math" for q in selected)
        if math_count != int(selection["math_task_count"]):
            raise ContractError("math task cardinality mismatch")
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
    selected_pairs = make_pairs(selected, int(config["seed"]), samples_per_task)

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
        "expected_cells": len(selected_pairs) * len(config.get("execution_arms", ["base", "moa"])),
        "expected_model_calls": {
            "base_main": len(selected_pairs)
            if "base" in config.get("execution_arms", ["base", "moa"])
            else 0,
            "moa_aggregator": len(selected_pairs)
            if "moa" in config.get("execution_arms", ["base", "moa"])
            else 0,
            "moa_references": (
                len(selected_pairs) * len(config["arms"]["moa"]["references"])
                if "moa" in config.get("execution_arms", ["base", "moa"])
                else 0
            ),
            "judge": 0,
            "total": len(selected_pairs)
            * sum(
                1 if arm == "base" else 1 + len(config["arms"]["moa"]["references"])
                for arm in config.get("execution_arms", ["base", "moa"])
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
            "retries": int(config.get("generation", {}).get("retries", 0)),
            "timeout_seconds": int(config.get("generation", {}).get("timeout_seconds", 900)),
            "order": "seeded shuffle of task/sample units; alternating arm-first order",
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
        env = os.environ.copy()
        env["HERMES_HOME"] = str(home)
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
        for arm_name in pair["order"]:
            verify_run_integrity(config_path, run_dir, manifest)
            result = invoke_arm(
                arm_name,
                config["arms"][arm_name],
                run_dir / "homes" / arm_name,
                question,
                effective_timeout(config),
            )
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
                    "provider": config["arms"][arm_name]["provider"],
                    "api_name": config["arms"][arm_name]["model"],
                    "reasoning_effort": config["arms"][arm_name]["reasoning_effort"],
                    "pair_id": pair["pair_id"],
                    "sample_index": pair["sample_index"],
                    "response_sha256": result["stdout_sha256"],
                },
            }
            with (raw_dir / f"hermes-{arm_name}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    validate_moa_traces(run_dir, expected_count=len(manifest["pairs"]))


def run_single_arm(config_path: Path, source_home: Path, run_dir: Path, arm_name: str) -> None:
    config = load_config(config_path)
    execution_arms = config.get("execution_arms")
    if execution_arms != [arm_name] or arm_name != "moa":
        raise ContractError("single-arm execution must be frozen as execution_arms: [moa]")
    manifest = prepare(config_path, source_home, run_dir)
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    by_id = {str(q["question_id"]): q for q in questions}
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True, mode=0o700)
    answer_path = raw_dir / "hermes-moa.jsonl"
    if answer_path.exists() and answer_path.stat().st_size:
        raise ContractError("run directory already contains MoA answers")
    for pair in manifest["pairs"]:
        verify_run_integrity(config_path, run_dir, manifest)
        question = by_id[pair["question_id"]]
        result = invoke_arm(
            "moa",
            config["arms"]["moa"],
            run_dir / "homes" / "moa",
            question,
            effective_timeout(config),
        )
        record = {
            "question_id": question["question_id"],
            "answer_id": sha256_bytes(f"{pair['pair_id']}:moa".encode())[:16],
            "sample_index": pair["sample_index"],
            "model_id": "hermes-moa-low",
            "choices": [{"index": 0, "turns": result["turns"]}],
            "tstamp": time.time(),
            "total_time_s": result["total_time_s"],
            "total_output_tokens": None,
            "total_input_tokens": None,
            "total_cached_tokens": None,
            "cost_usd": None,
            "api_info": {
                "provider": "moa",
                "api_name": config["arms"]["moa"]["model"],
                "reasoning_effort": config["arms"]["moa"]["reasoning_effort"],
                "pair_id": pair["pair_id"],
                "sample_index": pair["sample_index"],
                "response_sha256": result["stdout_sha256"],
            },
        }
        with answer_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    validate_moa_traces(run_dir, expected_count=len(manifest["pairs"]))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Paired Hermes BASE/MoA runner for LiveBench")
    p.add_argument("--config", type=Path, default=ROOT / "config/experiment.yaml")
    p.add_argument("--source-hermes-home", type=Path, default=Path.home() / ".hermes")
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="No-cost validation and manifest creation")
    prep.add_argument("--run-dir", type=Path, default=ROOT / "runs/smoke")
    execute = sub.add_parser("run", help="Execute paid paired model calls")
    execute.add_argument("--run-dir", type=Path, default=ROOT / "runs/smoke")

    execute_arm = sub.add_parser("run-arm", help="Execute a frozen single treatment arm")
    execute_arm.add_argument("--arm", choices=["moa"], required=True)
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
