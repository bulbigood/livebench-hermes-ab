from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .artifacts import FilesystemArtifactStore
from .config import ExperimentConfig, load_config
from .domain import ExclusionCode, HarnessError, IntegrityError
from .execution import CellRunner, ExecutionService
from .hermes import SubprocessHermesRunner, probe_compatibility, resolve_hermes_executable
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
    return min(32, max(1, (os.cpu_count() or 1) * 4)) if value == "auto" else int(value)


def _load_frozen(
    run_dir: Path,
) -> tuple[RunManifest, list[dict[str, object]], FilesystemArtifactStore]:
    manifest = parse_manifest((run_dir / "manifest.json").read_bytes())
    verify_frozen_artifacts(run_dir, manifest)
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    return manifest, questions, FilesystemArtifactStore(run_dir)


def command_prepare(args: argparse.Namespace, config: ExperimentConfig) -> dict[str, object]:
    executable = resolve_hermes_executable(args.hermes_executable)
    version, verified, warning = probe_compatibility(
        executable, config.compatibility.hermes_profile
    )
    manifest = prepare_run(
        ROOT,
        args.config,
        config,
        args.run_dir,
        CompatibilityResult(version, verified, warning),
    )
    return manifest_value(manifest)


def _service(
    args: argparse.Namespace, manifest: RunManifest, store: FilesystemArtifactStore
) -> ExecutionService:
    executable = resolve_hermes_executable(args.hermes_executable)

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
    if store.load_cell_outcomes():
        raise IntegrityError("run already has terminal outcomes; use resume")
    result = _service(args, manifest, store).execute(manifest.cells)
    if not result.complete:
        raise result.fatal or IntegrityError("execution incomplete")
    return {"status": "complete", "terminal_cells": len(result.outcomes)}


def command_resume(args: argparse.Namespace) -> dict[str, object]:
    manifest, _, store = _load_frozen(args.run_dir)
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
    result = _service(args, manifest, store).execute(
        tuple(by_id[cell] for cell in plan.cells), plan.attempts
    )
    if not result.complete:
        raise result.fatal or IntegrityError("execution incomplete")
    return {"status": "complete", "executed_cells": len(plan.cells)}


def command_score(args: argparse.Namespace) -> dict[str, object]:
    manifest, raw_questions, store = _load_frozen(args.run_dir)
    outcomes = store.load_committed_execution()
    questions = {
        str(q["question_id"]): QuestionEvidence(str(q["category"]), str(q["task"]), q)
        for q in raw_questions
    }
    pairs = tuple(dict.fromkeys(cell.id.pair_id for cell in manifest.cells))
    result = score_run(
        FrozenRun(manifest.arm_order, manifest.baseline_arm, pairs, outcomes, questions),
        registry({q.task for q in questions.values()}),
    )
    store.publish_scoring(scoring_bundle(result, render_markdown_report(result)))
    return {
        "status": "complete",
        "common_valid_pairs": len(result.common_pairs),
        "arm_means": dict(result.arm_means),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Typed multi-arm Hermes LiveBench harness")
    value.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    value.add_argument("--hermes-executable", type=Path)
    commands = value.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run", "resume", "score"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
        if name == "resume":
            command.add_argument("--retry-excluded", action="store_true")
    return value


def main() -> None:
    args = parser().parse_args()
    try:
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
