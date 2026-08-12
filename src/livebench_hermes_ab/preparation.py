from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path

import yaml

from .artifacts import FilesystemArtifactStore
from .config import ExperimentConfig
from .domain import ConfigError, IntegrityError
from .manifest import CompatibilityResult, Provenance, RunManifest, build_manifest
from .workload import Question, build_workload, question_from_record, select_questions


class CellWorkspace:
    def __init__(self, template: Path, cell_root: Path):
        self.home = Path(tempfile.mkdtemp(prefix="cell-", dir=cell_root))
        shutil.copytree(template, self.home, dirs_exist_ok=True, symlinks=True)

    def cleanup(self) -> None:
        shutil.rmtree(self.home)


class CellWorkspaceFactory:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.cell_root = run_dir / ".cell-homes"
        self.cell_root.mkdir(parents=True, exist_ok=True)

    def __call__(self, cell):
        template = self.run_dir / "homes" / cell.hermes_profile
        if not (template / "config.yaml").is_file():
            raise IntegrityError(f"missing prepared Hermes home: {cell.hermes_profile}")
        workspace = CellWorkspace(template, self.cell_root)
        config = yaml.safe_load((template / "config.yaml").read_text(encoding="utf-8"))
        moa = config.get("moa", {})
        if moa.get("enabled"):
            from .trace_validation import ExpectedTrace

            active = str(moa.get("active_preset") or moa["default_preset"])
            preset = moa["presets"][active]
            workspace.expected_trace = ExpectedTrace(
                cell.id,
                active,
                tuple((item["provider"], item["model"]) for item in preset["reference_models"]),
                (preset["aggregator"]["provider"], preset["aggregator"]["model"]),
            )
        return workspace


def _env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text.startswith("export "):
            text = text[7:].lstrip()
        if text and not text.startswith("#") and "=" in text:
            key, value = text.split("=", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def configure_arm_homes(
    output_root: Path,
    source_home: Path,
    arms: Iterable[tuple[str, Mapping[str, object], tuple[str, ...]]],
) -> None:
    source_values = _env_file(source_home / ".env")
    auth = source_home / "auth.json"
    if not auth.is_file():
        raise ConfigError(f"credential source missing: {auth}")
    for name, hermes, allowlist in arms:
        home = output_root / name
        home.mkdir(parents=True, mode=0o700)
        config_path = home / "config.yaml"
        config_path.write_text(yaml.safe_dump(_plain(hermes), sort_keys=False), encoding="utf-8")
        os.chmod(config_path, 0o600)
        (home / "auth.json").symlink_to(auth)
        resolved = {key: os.environ.get(key, source_values.get(key)) for key in allowlist}
        missing = sorted(key for key, value in resolved.items() if value is None)
        if missing:
            raise ConfigError(f"required credential keys missing: {missing}")
        env_path = home / ".env"
        env_path.write_text(
            "".join(f"{key}={resolved[key]}\n" for key in sorted(resolved)), encoding="utf-8"
        )
        os.chmod(env_path, 0o600)


def discover_questions(root: Path, globs: Iterable[str]) -> tuple[Question, ...]:
    paths = sorted({path for pattern in globs for path in root.glob(pattern)})
    if not paths:
        raise ConfigError("question discovery found no files")
    rows: list[Question] = []
    seen: set[str] = set()
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                question = question_from_record(json.loads(line))
            except (json.JSONDecodeError, ConfigError) as exc:
                raise ConfigError(f"invalid question at {path}:{line_number}") from exc
            if not question.question_id or question.question_id in seen:
                raise ConfigError(f"duplicate question: {question.question_id}")
            seen.add(question.question_id)
            rows.append(question)
    return tuple(rows)


def verify_upstream_revision(root: Path, expected: str) -> Provenance:
    process = subprocess.run(
        ["git", "-C", str(root / "upstream"), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    revision = process.stdout.strip()
    if process.returncode or revision != expected:
        raise IntegrityError(
            f"upstream revision mismatch: expected {expected}, got {revision or 'unavailable'}"
        )
    return Provenance(revision)


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


def prepare_run(
    root: Path,
    config_path: Path,
    config: ExperimentConfig,
    run_dir: Path,
    compatibility: CompatibilityResult,
    source_home: Path | None = None,
) -> RunManifest:
    provenance = verify_upstream_revision(root, config.upstream_commit)
    selected = select_questions(discover_questions(root, config.question_globs), config.selection)
    workload = build_workload(
        selected, config.arms, config.generation.samples_per_task, config.seed
    )
    if run_dir.exists():
        raise IntegrityError(f"run directory already exists: {run_dir}")
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{run_dir.name}.", dir=run_dir.parent))
    try:
        store = FilesystemArtifactStore(stage)
        config_bytes = config_path.read_bytes()
        questions = [_plain(question.raw) for question in selected]
        question_bytes = (json.dumps(questions, sort_keys=True, ensure_ascii=False) + "\n").encode()
        profile_bytes = {
            f"homes/{arm.name}/config.yaml": yaml.safe_dump(
                _plain(arm.hermes), sort_keys=False
            ).encode()
            for arm in config.arms
        }
        manifest = build_manifest(
            config,
            workload,
            provenance,
            compatibility,
            frozen_files={
                "config.snapshot.yaml": config_bytes,
                "questions.json": question_bytes,
                **profile_bytes,
            },
        )
        store.write_manifest(manifest)
        (stage / "config.snapshot.yaml").write_bytes(config_bytes)
        (stage / "questions.json").write_bytes(question_bytes)
        configure_arm_homes(
            stage / "homes",
            (source_home or Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))).resolve(),
            ((arm.name, arm.hermes, arm.credential_env) for arm in config.arms),
        )
        (stage / "prepared.complete").write_text("2\n", encoding="ascii")
        os.replace(stage, run_dir)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
