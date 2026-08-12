from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .agentic import AgenticStatus, SidecarRequest, load_agentic_cohort, run_sidecar
from .agentic_vertical import run_no_provider_vertical
from .domain import HarnessError


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def command_run(args: argparse.Namespace) -> int:
    cohort = load_agentic_cohort(args.cohort)
    request = SidecarRequest.from_json(args.request.read_text(encoding="utf-8"))
    result = run_sidecar(cohort, request)
    output = result.to_json()
    if args.output:
        _atomic_write(args.output, output)
    sys.stdout.write(output)
    return 0 if result.reason_code is None else 2


def command_phase0(args: argparse.Namespace) -> int:
    cohort = load_agentic_cohort(args.cohort)
    results = []
    complete = True
    for task in cohort.tasks:
        evidence = args.evidence_root / task.instance_id
        for mode in ("empty", "gold", "wrong"):
            result = run_sidecar(cohort, SidecarRequest(1, task.instance_id, mode, evidence))
            results.append(json.loads(result.to_json()))
            expected = AgenticStatus.RESOLVED if mode == "gold" else AgenticStatus.UNRESOLVED
            complete &= result.status is expected and result.reason_code is None
    payload = (
        json.dumps(
            {
                "schema_version": 1,
                "status": "complete" if complete else "failed",
                "source_revision": cohort.source_revision,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    _atomic_write(args.output, payload)
    sys.stdout.write(payload)
    return 0 if complete else 2


def command_vertical(args: argparse.Namespace) -> int:
    cohort = load_agentic_cohort(args.cohort)
    payload = run_no_provider_vertical(cohort, args.evidence_root, args.output_root)
    output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _atomic_write(args.output, output)
    sys.stdout.write(output)
    return 0 if payload["status"] == "complete" else 2


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Typed no-provider Agentic Coding sidecar")
    value.add_argument("--cohort", type=Path, required=True)
    commands = value.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--request", type=Path, required=True)
    run.add_argument("--output", type=Path)
    phase0 = commands.add_parser("phase0")
    phase0.add_argument("--evidence-root", type=Path, required=True)
    phase0.add_argument("--output", type=Path, required=True)
    vertical = commands.add_parser("vertical")
    vertical.add_argument("--evidence-root", type=Path, required=True)
    vertical.add_argument("--output-root", type=Path, required=True)
    vertical.add_argument("--output", type=Path, required=True)
    return value


def main() -> None:
    args = parser().parse_args()
    try:
        handlers = {
            "run": command_run,
            "phase0": command_phase0,
            "vertical": command_vertical,
        }
        code = handlers[args.command](args)
    except (HarnessError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
