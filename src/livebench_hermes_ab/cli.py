from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .artifacts import FilesystemArtifactStore
from .config import ExperimentConfig, load_config
from .domain import ExclusionCode, HarnessError, IntegrityError
from .execution import CellRunner, ExecutionService
from .hermes import (
    SubprocessHermesRunner,
    materialize_git_source,
    probe_compatibility,
    resolve_hermes_command,
)
from .manifest import (
    CompatibilityResult,
    RunManifest,
    manifest_value,
    parse_manifest,
    verify_frozen_artifacts,
)
from .preparation import CellWorkspaceFactory, prepare_run
from .report import render_markdown_report
from .resume import ResumePolicy, plan_resume
from .scheduler import Scheduler
from .scoring import FrozenRun, QuestionEvidence, score_run, scoring_bundle
from .scoring_adapters import registry

ROOT = Path(__file__).resolve().parents[2]


def _workers(value: int | str) -> int:
    return min(40, max(1, (os.cpu_count() or 1) * 5)) if value == "auto" else int(value)


def _default_run_dir() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "runs" / f"smoke-{stamp}"


def _pipeline_config(config_path: Path, full: bool) -> tuple[ExperimentConfig, Path | None]:
    config = load_config(config_path)
    if full or config.generation.samples_per_task == 1:
        return config, None
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw["generation"]["samples_per_task"] = 1
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="livebench-smoke-", delete=False, encoding="utf-8"
    ) as handle:
        yaml.safe_dump(raw, handle, sort_keys=False)
        path = Path(handle.name)
    return replace(config, generation=replace(config.generation, samples_per_task=1)), path


def _load_frozen(
    run_dir: Path,
) -> tuple[RunManifest, list[dict[str, object]], FilesystemArtifactStore]:
    manifest = parse_manifest((run_dir / "manifest.json").read_bytes())
    verify_frozen_artifacts(run_dir, manifest)
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    return manifest, questions, FilesystemArtifactStore(run_dir)


def command_prepare(args: argparse.Namespace, config: ExperimentConfig) -> dict[str, object]:
    source = config.compatibility.hermes
    source_directory = ROOT
    if source.mode == "git" and args.hermes_executable is None:
        source_directory = materialize_git_source(
            source, ROOT / ".cache" / "hermes" / str(source.commit)
        )
    executable = resolve_hermes_command(source, source_directory, args.hermes_executable)
    version, verified, warning = probe_compatibility(executable, source)
    manifest = prepare_run(
        ROOT,
        args.config,
        config,
        args.run_dir,
        CompatibilityResult(version, verified, warning),
        credentials_file=args.credentials_file,
    )
    return manifest_value(manifest)


def _service(
    args: argparse.Namespace,
    manifest: RunManifest,
    store: FilesystemArtifactStore,
    config: ExperimentConfig,
) -> ExecutionService:
    source = config.compatibility.hermes
    source_directory = (
        ROOT / ".cache" / "hermes" / str(source.commit)
        if source.mode == "git"
        else ROOT
    )
    executable = resolve_hermes_command(source, source_directory, args.hermes_executable)

    runner = CellRunner(
        SubprocessHermesRunner(executable),
        CellWorkspaceFactory(args.run_dir),
        manifest.timeout_seconds,
    )
    return ExecutionService(
        Scheduler(_workers(manifest.workers), manifest.execution_mode), runner, store
    )


def command_run(args: argparse.Namespace) -> dict[str, object]:
    manifest, _, store = _load_frozen(args.run_dir)
    config = load_config(args.run_dir / "config.snapshot.yaml")
    if store.load_cell_outcomes():
        raise IntegrityError("run already has terminal outcomes; use resume")
    result = _service(args, manifest, store, config).execute(manifest.cells)
    if not result.complete:
        raise result.fatal or IntegrityError("execution incomplete")
    return {"status": "complete", "terminal_cells": len(result.outcomes)}


def command_resume(args: argparse.Namespace) -> dict[str, object]:
    manifest, _, store = _load_frozen(args.run_dir)
    config = load_config(args.run_dir / "config.snapshot.yaml")
    retryable = (
        frozenset(ExclusionCode)
        if args.retry_excluded
        else frozenset(ExclusionCode(code) for code in manifest.retryable_codes)
    )
    plan = plan_resume(
        store.load_cell_outcomes(),
        tuple(cell.id for cell in manifest.cells),
        ResumePolicy(manifest.max_attempts, retryable),
        store,
    )
    by_id = {cell.id: cell for cell in manifest.cells}
    result = _service(args, manifest, store, config).execute(
        tuple(by_id[cell] for cell in plan.cells), plan.attempts
    )
    if not result.complete:
        raise result.fatal or IntegrityError("execution incomplete")
    return {"status": "complete", "executed_cells": len(plan.cells)}


def command_score(args: argparse.Namespace) -> dict[str, object]:
    manifest, raw_questions, store = _load_frozen(args.run_dir)
    frozen_config = load_config(args.run_dir / "config.snapshot.yaml")
    outcomes = store.load_committed_execution()
    questions = {
        str(q["question_id"]): QuestionEvidence(str(q["category"]), str(q["task"]), q)
        for q in raw_questions
    }
    pairs = tuple(dict.fromkeys(cell.id.pair_id for cell in manifest.cells))
    sample_counts = {
        len({cell.id.sample_index for cell in manifest.cells if cell.id.question_id == question_id})
        for question_id in questions
    }
    if len(sample_counts) != 1:
        raise IntegrityError("inconsistent samples per task in frozen workload")
    samples_per_task = sample_counts.pop()
    result = score_run(
        FrozenRun(
            manifest.arm_order,
            manifest.baseline_arm,
            pairs,
            outcomes,
            questions,
            samples_per_task=samples_per_task,
            confidence_level=frozen_config.scoring.confidence_level,
            target_margin_of_error=frozen_config.scoring.target_margin_of_error,
        ),
        registry({q.task for q in questions.values()}),
    )
    store.publish_scoring(scoring_bundle(result, render_markdown_report(result)))
    return {
        "status": "complete",
        "common_valid_pairs": len(result.common_pairs),
        "arm_means": dict(result.arm_means),
    }


def command_pipeline(args: argparse.Namespace) -> dict[str, object]:
    run_dir = args.run_dir or _default_run_dir()
    config, temporary_config = _pipeline_config(args.config, args.full)
    config_path = temporary_config or args.config
    pipeline_args = argparse.Namespace(
        config=config_path,
        hermes_executable=args.hermes_executable,
        run_dir=run_dir,
        credentials_file=args.credentials_file,
    )
    try:
        command_prepare(pipeline_args, config)
        execution = command_run(pipeline_args)
        scoring = command_score(pipeline_args)
        return {
            "status": "complete",
            "run_dir": str(run_dir),
            "samples_per_task": config.generation.samples_per_task,
            "execution": execution,
            "scoring": scoring,
        }
    finally:
        if temporary_config is not None:
            temporary_config.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Typed multi-arm Hermes LiveBench harness")
    value.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    value.add_argument("--hermes-executable", type=Path)
    value.add_argument(
        "--full",
        action="store_true",
        help="use generation.samples_per_task from config; default pipeline uses one sample",
    )
    value.add_argument("--run-dir", type=Path, help="pipeline output directory")
    value.add_argument(
        "--credentials-file",
        type=Path,
        help="pipeline dotenv secret source; defaults to $HERMES_HOME/.env",
    )
    commands = value.add_subparsers(dest="command")
    for name in ("prepare", "run", "resume", "score"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
        if name == "prepare":
            command.add_argument(
                "--credentials-file",
                type=Path,
                help="dotenv secret source; defaults to $HERMES_HOME/.env",
            )
        if name == "resume":
            command.add_argument("--retry-excluded", action="store_true")
    return value


def main() -> None:
    args = parser().parse_args()
    try:
        if args.command is None:
            print(json.dumps(command_pipeline(args), indent=2, ensure_ascii=False))
            return
        if args.full:
            raise ValueError("--full is only valid for the default pipeline")
        config = load_config(args.config) if args.command == "prepare" else None
        handler = {
            "prepare": lambda: command_prepare(args, config),
            "run": lambda: command_run(args),
            "resume": lambda: command_resume(args),
            "score": lambda: command_score(args),
        }[args.command]
        print(json.dumps(handler(), indent=2, ensure_ascii=False))
    except (HarnessError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
