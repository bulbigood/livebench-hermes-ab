from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import yaml

from .domain import ConfigError, ExclusionCode


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int
    retryable_codes: frozenset[ExclusionCode]


@dataclass(frozen=True, slots=True)
class ScoringContract:
    implementation: Literal["livebench-objective-ground-truth"]
    schema_version: int
    confidence_level: float = 0.95
    target_margin_of_error: float = 0.05


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    mode: Literal["streaming", "balanced_waves"]
    workers: int | Literal["auto"]
    timeout_seconds: int


@dataclass(frozen=True, slots=True)
class HermesSourceConfig:
    mode: Literal["release", "git", "directory"]
    release: str | None = None
    repository: str | None = None
    commit: str | None = None
    directory: str | None = None


@dataclass(frozen=True, slots=True)
class CompatibilityConfig:
    hermes: HermesSourceConfig


@dataclass(frozen=True, slots=True)
class SelectionConfig:
    scenarios: Mapping[str, tuple[Mapping[str, str], ...]]


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    samples_per_task: int
    retry: RetryPolicy


@dataclass(frozen=True, slots=True)
class ArmConfig:
    name: str
    credential_env: tuple[str, ...]
    hermes: Mapping[str, object]
    kind: Literal["plain", "moa"]

    @property
    def expected_provider_calls(self) -> int:
        if self.kind == "plain":
            return 1
        moa = self.hermes["moa"]
        assert isinstance(moa, Mapping)
        presets = moa["presets"]
        assert isinstance(presets, Mapping)
        active = str(moa.get("active_preset") or moa["default_preset"])
        preset = presets[active]
        assert isinstance(preset, Mapping)
        return 1 + len(preset["reference_models"])  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    experiment_id: str
    upstream_commit: str
    release: str
    seed: int
    question_globs: tuple[str, ...]
    baseline_arm: str
    arms: tuple[ArmConfig, ...]
    selection: SelectionConfig
    generation: GenerationConfig
    execution: ExecutionConfig
    compatibility: CompatibilityConfig
    scoring: ScoringContract


def validate_balanced_workers(config: ExperimentConfig) -> None:
    if config.execution.mode != "balanced_waves":
        return
    workers = config.execution.workers
    arm_count = len(config.arms)
    if workers == "auto":
        raise ConfigError("balanced_waves requires an explicit worker count")
    if workers % arm_count:
        raise ConfigError(
            f"balanced_waves workers must be a multiple of the {arm_count} arms; got {workers}"
        )


def _mapping(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must be a mapping")
    return value


def _keys(
    value: dict[str, object],
    required: set[str],
    path: str,
    optional: set[str] = frozenset(),
) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if extra:
        raise ConfigError(f"{path} contains unsupported keys: {sorted(extra)}")
    if missing:
        raise ConfigError(f"{path} missing required keys: {sorted(missing)}")


def _positive_int(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigError(f"{path} must be a positive integer")
    return value


def _parse_hermes_source(value: object) -> HermesSourceConfig:
    source = _mapping(value, "compatibility.hermes")
    keys = set(source)
    if keys == {"release"}:
        release = source["release"]
        if not isinstance(release, str) or not re.fullmatch(r"\d+\.\d+\.\d+", release):
            raise ConfigError("compatibility.hermes.release must be a semantic version")
        return HermesSourceConfig("release", release=release)
    if keys <= {"repository", "commit"} and keys:
        if keys != {"repository", "commit"}:
            raise ConfigError("compatibility.hermes git mode requires repository and commit")
        repository, commit = source["repository"], source["commit"]
        if not isinstance(repository, str) or not repository.strip():
            raise ConfigError("compatibility.hermes.repository must be non-empty")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
            raise ConfigError("compatibility.hermes.commit must be a full 40-character SHA")
        return HermesSourceConfig("git", repository=repository, commit=commit.lower())
    if keys == {"directory"}:
        directory = source["directory"]
        if (
            not isinstance(directory, str)
            or not directory.strip()
            or not Path(directory).expanduser().is_absolute()
        ):
            raise ConfigError("compatibility.hermes.directory must be an absolute path")
        return HermesSourceConfig("directory", directory=directory)
    raise ConfigError("compatibility.hermes must select exactly one source mode")


def _parse_selection(value: object) -> SelectionConfig:
    selection = _mapping(value, "selection")
    _keys(selection, {"scenarios"}, "selection")
    groups = _mapping(selection["scenarios"], "selection.scenarios")
    frozen: dict[str, tuple[Mapping[str, str], ...]] = {}
    allowed = {"id", "family", "source_url", "note"}
    for category, raw_entries in groups.items():
        if not isinstance(raw_entries, list) or not raw_entries:
            raise ConfigError(f"selection.scenarios.{category} must be a non-empty list")
        entries = []
        for raw in raw_entries:
            entry = _mapping(raw, f"selection.scenarios.{category}[]")
            if not {"id", "family"} <= entry.keys() or entry.keys() - allowed:
                raise ConfigError(f"invalid scenario in {category}")
            if not all(isinstance(item, str) and item for item in entry.values()):
                raise ConfigError(f"scenario values in {category} must be non-empty strings")
            entries.append(MappingProxyType(dict(entry)))
        frozen[str(category)] = tuple(entries)
    return SelectionConfig(MappingProxyType(frozen))


def _parse_arms(value: object) -> tuple[ArmConfig, ...]:
    arms_value = _mapping(value, "arms")
    if not arms_value:
        raise ConfigError("arms must not be empty")
    arms: list[ArmConfig] = []
    for name, raw_arm in arms_value.items():
        arm = _mapping(raw_arm, f"arms.{name}")
        _keys(arm, {"credential_env", "hermes"}, f"arms.{name}")
        hermes = _mapping(arm["hermes"], f"arms.{name}.hermes")
        _keys(hermes, {"model", "agent", "moa"}, f"arms.{name}.hermes")
        model = _mapping(hermes["model"], f"arms.{name}.hermes.model")
        _keys(model, {"provider", "default"}, f"arms.{name}.hermes.model")
        agent = _mapping(hermes["agent"], f"arms.{name}.hermes.agent")
        extra_agent = agent.keys() - {"reasoning_effort", "disabled_toolsets"}
        if extra_agent:
            raise ConfigError(
                f"arms.{name}.hermes.agent contains unsupported keys: {sorted(extra_agent)}"
            )
        moa = _mapping(hermes["moa"], f"arms.{name}.hermes.moa")
        if not isinstance(moa.get("enabled"), bool):
            raise ConfigError(f"arms.{name}.hermes.moa.enabled must be boolean")
        kind = "moa" if moa["enabled"] else "plain"
        expected_moa = (
            {"enabled", "save_traces"}
            if kind == "plain"
            else {"enabled", "default_preset", "active_preset", "save_traces", "presets"}
        )
        _keys(moa, expected_moa, f"arms.{name}.hermes.moa")
        if kind == "moa":
            _validate_presets(name, moa)
        arms.append(
            ArmConfig(str(name), tuple(arm["credential_env"]), MappingProxyType(hermes), kind)
        )  # type: ignore[arg-type]
    return tuple(arms)


def _validate_presets(name: str, moa: dict[str, object]) -> None:
    presets = _mapping(moa["presets"], f"arms.{name}.hermes.moa.presets")
    active = str(moa["active_preset"])
    if active != moa["default_preset"] or active not in presets:
        raise ConfigError(f"arms.{name} must name one active/default preset")
    preset = _mapping(presets[active], f"arms.{name}.hermes.moa.presets.{active}")
    _keys(
        preset,
        {
            "enabled",
            "degraded_reference_policy",
            "reference_max_tokens",
            "max_tokens",
            "fanout",
            "reference_models",
            "aggregator",
        },
        f"arms.{name}.hermes.moa.presets.{active}",
    )
    aggregator = _mapping(preset["aggregator"], f"arms.{name}.aggregator")
    _keys(aggregator, {"provider", "model", "reasoning_effort"}, f"arms.{name}.aggregator")
    references = preset["reference_models"]
    if not isinstance(references, list) or not references:
        raise ConfigError(f"arms.{name} requires reference models")
    for index, raw in enumerate(references):
        reference = _mapping(raw, f"arms.{name}.reference_models[{index}]")
        _keys(reference, {"provider", "model"}, f"arms.{name}.reference_models[{index}]")


def parse_config(value: object) -> ExperimentConfig:
    root = _mapping(value, "config")
    _keys(
        root,
        {"experiment", "selection", "generation", "execution", "compatibility", "arms", "scoring"},
        "config",
    )
    experiment = _mapping(root["experiment"], "experiment")
    _keys(experiment, {"id", "upstream_commit", "release", "seed", "question_globs"}, "experiment")
    generation = _mapping(root["generation"], "generation")
    _keys(generation, {"samples_per_task", "retry"}, "generation")
    retry = _mapping(generation["retry"], "generation.retry")
    _keys(retry, {"max_attempts", "retryable_codes"}, "generation.retry")
    try:
        codes = frozenset(ExclusionCode(str(code)) for code in retry["retryable_codes"])  # type: ignore[union-attr]
    except (TypeError, ValueError) as exc:
        raise ConfigError("generation.retry.retryable_codes is invalid") from exc
    execution = _mapping(root["execution"], "execution")
    _keys(execution, {"mode", "workers", "timeout_seconds", "baseline_arm"}, "execution")
    mode = execution["mode"]
    if mode not in {"streaming", "balanced_waves"}:
        raise ConfigError("execution.mode must be streaming or balanced_waves")
    workers = execution["workers"]
    if workers != "auto":
        workers = _positive_int(workers, "execution.workers")
    compatibility = _mapping(root["compatibility"], "compatibility")
    _keys(compatibility, {"hermes"}, "compatibility")
    hermes_compat = _mapping(compatibility["hermes"], "compatibility.hermes")
    scoring = _mapping(root["scoring"], "scoring")
    _keys(
        scoring,
        {"implementation", "schema_version"},
        "scoring",
        {"confidence_level", "target_margin_of_error"},
    )
    if (
        scoring["implementation"] != "livebench-objective-ground-truth"
        or scoring["schema_version"] != 2
    ):
        raise ConfigError("unsupported scoring contract")
    confidence_level = float(scoring.get("confidence_level", 0.95))
    target_margin = float(scoring.get("target_margin_of_error", 0.05))
    if not 0 < confidence_level < 1:
        raise ConfigError("scoring.confidence_level must be between 0 and 1")
    if not 0 < target_margin < 1:
        raise ConfigError("scoring.target_margin_of_error must be between 0 and 1")
    arms = _parse_arms(root["arms"])
    baseline = execution["baseline_arm"]
    if baseline not in {arm.name for arm in arms}:
        raise ConfigError("execution.baseline_arm must name an arm")
    config = ExperimentConfig(
        experiment_id=str(experiment["id"]),
        upstream_commit=str(experiment["upstream_commit"]),
        release=str(experiment["release"]),
        seed=int(experiment["seed"]),
        question_globs=tuple(experiment["question_globs"]),
        baseline_arm=str(baseline),
        arms=arms,
        selection=_parse_selection(root["selection"]),
        generation=GenerationConfig(
            _positive_int(generation["samples_per_task"], "generation.samples_per_task"),
            RetryPolicy(
                _positive_int(retry["max_attempts"], "generation.retry.max_attempts"), codes
            ),
        ),
        execution=ExecutionConfig(
            mode, workers, _positive_int(execution["timeout_seconds"], "execution.timeout_seconds")
        ),  # type: ignore[arg-type]
        compatibility=CompatibilityConfig(_parse_hermes_source(hermes_compat)),
        scoring=ScoringContract(
            "livebench-objective-ground-truth", 2, confidence_level, target_margin
        ),
    )
    validate_balanced_workers(config)
    return config


def load_config(path: Path) -> ExperimentConfig:
    try:
        return parse_config(yaml.safe_load(path.read_text(encoding="utf-8")))
    except OSError as exc:
        raise ConfigError(f"cannot read config: {path}") from exc
