from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
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
    resolve_explicit_scenarios,
    select_stratified_complexity,
    sha256_bytes,
    validate_frozen_selection,
    validate_treatment_boundary,
)
from .trace_validation import validate_moa_trace_record, validate_moa_traces

ROOT = Path(__file__).resolve().parents[2]
WORKERS_PER_CPU = 4
MAX_WORKERS = 32
RETRYABLE_EXCLUSION_CODES = {"CELL_TIMEOUT", "MODEL_OR_PROVIDER_FAILURE", "INVALID_MOA_TRACE"}


class CellExecutionError(RuntimeError):
    """A provider/model failure confined to one benchmark cell."""


_CPU_COUNT_UNSET = object()

SUPPORTED_HERMES_PROFILES = {"0.19.1"}
VALID_REASONING_EFFORTS = {
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
    "ultra",
}
MODEL_KEYS_0_19_1 = {
    "default",
    "provider",
    "base_url",
    "api_key",
    "context_length",
    "aliases",
}
AGENT_KEYS_0_19_1 = {
    "reasoning_effort",
    "reasoning_overrides",
    "disabled_toolsets",
    "max_turns",
    "completion_reserve_turns",
    "api_max_retries",
    "service_tier",
    "tool_use_enforcement",
    "intent_ack_continuation",
    "task_completion_guidance",
    "parallel_tool_call_guidance",
    "environment_probe",
    "environment_hint",
    "coding_context",
    "coding_instructions",
    "verify_guidance",
    "max_verify_nudges",
    "verify_on_stop",
}
MOA_KEYS_0_19_1 = {
    "enabled",
    "default_preset",
    "active_preset",
    "save_traces",
    "trace_dir",
    "privacy_filter",
    "presets",
}
MOA_PRESET_KEYS_0_19_1 = {
    "enabled",
    "degraded_reference_policy",
    "reference_max_tokens",
    "max_tokens",
    "fanout",
    "reference_models",
    "aggregator",
}
MOA_MODEL_SLOT_KEYS_0_19_1 = {
    "provider",
    "model",
    "reasoning_effort",
    "base_url",
    "api_key",
    "extra_body",
}

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


def resolve_worker_count(value: Any = None, *, cpu_count: Any = _CPU_COUNT_UNSET) -> int:
    if value is None or value == "auto":
        detected = os.cpu_count() if cpu_count is _CPU_COUNT_UNSET else cpu_count
        effective_cpus = detected if isinstance(detected, int) and detected > 0 else 1
        return min(effective_cpus * WORKERS_PER_CPU, MAX_WORKERS)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"execution.workers must be an integer from 1 to {MAX_WORKERS}")
    if not 1 <= value <= MAX_WORKERS:
        raise ContractError(f"execution.workers must be from 1 to {MAX_WORKERS}")
    return value


def schedule_cells(
    pairs: list[dict[str, Any]],
    arm_names: tuple[str, ...],
    *,
    scheduling: str,
    workers: int,
) -> list[list[dict[str, Any]]]:
    if scheduling not in {"streaming", "balanced_waves"}:
        raise ContractError("execution.scheduling must be streaming or balanced_waves")
    if not arm_names:
        raise ContractError("execution requires at least one arm")
    groups: list[list[dict[str, Any]]] = []
    for index, pair in enumerate(pairs):
        offset = index % len(arm_names)
        rotated = arm_names[offset:] + arm_names[:offset]
        groups.append([{**pair, "arm_name": arm_name} for arm_name in rotated])
    if scheduling == "streaming":
        return [[cell for group in groups for cell in group]]
    if workers < len(arm_names):
        raise ContractError("balanced_waves workers must be at least the number of arms")
    groups_per_wave = max(1, workers // len(arm_names))
    return [
        [cell for group in groups[start : start + groups_per_wave] for cell in group]
        for start in range(0, len(groups), groups_per_wave)
    ]


def resolve_execution(
    config: dict[str, Any],
    *,
    scheduling_override: str | None = None,
    workers_override: int | None = None,
) -> dict[str, Any]:
    execution = config.get("execution", {})
    scheduling = scheduling_override or execution.get("scheduling")
    if scheduling is None:
        scheduling = (
            "balanced_waves" if execution.get("parallelism") == "paired_arms" else "streaming"
        )
    workers = resolve_worker_count(
        workers_override if workers_override is not None else execution.get("workers")
    )
    arm_count = len(config.get("arms", {}))
    if scheduling == "balanced_waves" and workers < arm_count:
        raise ContractError("balanced_waves workers must be at least the number of arms")
    if scheduling not in {"streaming", "balanced_waves"}:
        raise ContractError("execution.scheduling must be streaming or balanced_waves")
    effective_workers = (
        workers - (workers % arm_count) if scheduling == "balanced_waves" and arm_count else workers
    )
    return {
        "scheduling": scheduling,
        "requested_workers": workers,
        "effective_workers": effective_workers,
        "timing_comparable": scheduling == "balanced_waves",
    }


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
            "compatibility": raw.get("compatibility", {}),
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
        raise ContractError("multi-arm experiments require at least two arms")
    workers_per_arm = config.get("execution", {}).get("workers_per_arm")
    if workers_per_arm not in (None, 1):
        raise ContractError("legacy execution.workers_per_arm must be exactly 1")
    resolve_execution(config)
    profile = config.get("compatibility", {}).get("hermes", {}).get("profile")
    if profile not in SUPPORTED_HERMES_PROFILES:
        supported = ", ".join(sorted(SUPPORTED_HERMES_PROFILES))
        raise ContractError(
            f"compatibility.hermes.profile must name a supported profile: {supported}"
        )
    for name, arm in arms.items():
        if not name.replace("-", "").replace("_", "").isalnum():
            raise ContractError(f"unsafe arm name: {name}")
        hermes = arm.get("hermes")
        if not isinstance(hermes, dict):
            raise ContractError(f"arm {name} requires a hermes table")
        validate_hermes_arm_schema(name, arm, str(profile))
        credentials = arm.get("credential_env", [])
        if not isinstance(credentials, list) or not all(
            isinstance(key, str) for key in credentials
        ):
            raise ContractError(f"arm {name} credential_env must be a list of names")


def _unknown_keys(value: Any, allowed: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return []
    return sorted(str(key) for key in value if key not in allowed)


def _require_mapping(arm_name: str, path: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"arm {arm_name} Hermes {path} must be a mapping")
    return value


def _require_nonempty_string(arm_name: str, path: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"arm {arm_name} Hermes {path} must be a non-empty string")
    return value.strip()


def _validate_reasoning(arm_name: str, path: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, str):
        raise ContractError(f"arm {arm_name} Hermes {path} must be a reasoning string")
    if value.strip().lower() not in VALID_REASONING_EFFORTS:
        allowed = ", ".join(sorted(VALID_REASONING_EFFORTS))
        raise ContractError(f"arm {arm_name} Hermes {path} must be one of: {allowed}")


def _reject_unknown(arm_name: str, path: str, value: Any, allowed: set[str]) -> None:
    unknown = _unknown_keys(value, allowed)
    if unknown:
        raise ContractError(f"arm {arm_name} Hermes {path} has unsupported keys: {unknown}")


def _reject_inline_credentials(arm_name: str, value: Any, path: str = "config") -> None:
    sensitive_names = {
        "api_key",
        "api_token",
        "access_token",
        "refresh_token",
        "auth_token",
        "password",
        "secret",
        "client_secret",
        "private_key",
        "credential",
        "credentials",
    }
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            child_path = f"{path}.{key}"
            normalized = key.strip().lower().replace("-", "_")
            if normalized in sensitive_names and child not in (None, "", False, [], {}):
                raise ContractError(
                    f"arm {arm_name} Hermes {child_path} contains an inline credential; "
                    "pass only its environment-variable name through credential_env"
                )
            _reject_inline_credentials(arm_name, child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_inline_credentials(arm_name, child, f"{path}[{index}]")


def validate_hermes_arm_schema(arm_name: str, arm: dict[str, Any], profile: str) -> None:
    if profile != "0.19.1":
        raise ContractError(f"unsupported Hermes compatibility profile: {profile}")
    hermes = _require_mapping(arm_name, "config", arm.get("hermes"))
    _reject_inline_credentials(arm_name, hermes)
    model = _require_mapping(arm_name, "model", hermes.get("model"))
    agent = _require_mapping(arm_name, "agent", hermes.get("agent"))
    moa = _require_mapping(arm_name, "moa", hermes.get("moa"))
    _reject_unknown(arm_name, "model", model, MODEL_KEYS_0_19_1)
    _reject_unknown(arm_name, "agent", agent, AGENT_KEYS_0_19_1)
    _reject_unknown(arm_name, "moa", moa, MOA_KEYS_0_19_1)

    provider = _require_nonempty_string(arm_name, "model.provider", model.get("provider"))
    _require_nonempty_string(arm_name, "model.default", model.get("default"))
    _validate_reasoning(arm_name, "agent.reasoning_effort", agent.get("reasoning_effort"))
    disabled = agent.get("disabled_toolsets", [])
    if not isinstance(disabled, list) or not all(isinstance(item, str) for item in disabled):
        raise ContractError(f"arm {arm_name} Hermes agent.disabled_toolsets must be strings")

    enabled = moa.get("enabled")
    if not isinstance(enabled, bool):
        raise ContractError(f"arm {arm_name} Hermes moa.enabled must be boolean")
    save_traces = moa.get("save_traces")
    if not isinstance(save_traces, bool):
        raise ContractError(f"arm {arm_name} Hermes moa.save_traces must be boolean")
    if not enabled:
        if provider == "moa":
            raise ContractError(f"arm {arm_name} uses provider moa but Hermes moa.enabled is false")
        return
    if provider != "moa":
        raise ContractError(f"arm {arm_name} enables MoA but model.provider is not moa")
    if not save_traces:
        raise ContractError(f"arm {arm_name} MoA requires moa.save_traces: true for auditability")

    active = _require_nonempty_string(
        arm_name, "moa.active_preset", moa.get("active_preset") or moa.get("default_preset")
    )
    presets = _require_mapping(arm_name, "moa.presets", moa.get("presets"))
    if active not in presets:
        raise ContractError(f"arm {arm_name} Hermes active MoA preset not found: {active}")
    preset = _require_mapping(arm_name, f"moa.presets.{active}", presets[active])
    _reject_unknown(arm_name, f"moa.presets.{active}", preset, MOA_PRESET_KEYS_0_19_1)
    if preset.get("enabled", True) is not True:
        raise ContractError(f"arm {arm_name} Hermes active MoA preset must be enabled")
    references = preset.get("reference_models")
    if not isinstance(references, list) or not references:
        raise ContractError(f"arm {arm_name} Hermes active MoA preset needs reference_models")
    slots = [(f"reference_models[{index}]", slot) for index, slot in enumerate(references)]
    slots.append(("aggregator", preset.get("aggregator")))
    for slot_path, raw_slot in slots:
        slot = _require_mapping(arm_name, f"moa.presets.{active}.{slot_path}", raw_slot)
        _reject_unknown(
            arm_name,
            f"moa.presets.{active}.{slot_path}",
            slot,
            MOA_MODEL_SLOT_KEYS_0_19_1,
        )
        slot_provider = _require_nonempty_string(
            arm_name, f"moa.presets.{active}.{slot_path}.provider", slot.get("provider")
        )
        _require_nonempty_string(
            arm_name, f"moa.presets.{active}.{slot_path}.model", slot.get("model")
        )
        if slot_provider == "moa":
            raise ContractError(f"arm {arm_name} Hermes nested MoA providers are unsupported")
        if "reasoning_effort" in slot:
            _validate_reasoning(
                arm_name,
                f"moa.presets.{active}.{slot_path}.reasoning_effort",
                slot["reasoning_effort"],
            )


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
            "reference_max_tokens": 50000,
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


def resolve_hermes_executable(explicit: Path | str | None = None) -> str:
    if explicit is not None:
        candidate = Path(explicit).expanduser().resolve()
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise ContractError(
                f"explicit Hermes executable is missing or not executable: {candidate}"
            )
        return str(candidate)
    env_candidate = os.environ.get("HERMES_EXECUTABLE")
    if env_candidate:
        return resolve_hermes_executable(env_candidate)
    resolved = shutil.which("hermes")
    if not resolved:
        raise ContractError(
            "Hermes executable not found; pass --hermes-executable, set "
            "HERMES_EXECUTABLE, or install Hermes on PATH"
        )
    return str(Path(resolved).resolve())


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


def prepare(
    config_path: Path,
    source_home: Path,
    run_dir: Path,
    hermes_executable: str | None = None,
    *,
    scheduling_override: str | None = None,
    workers_override: int | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    execution = resolve_execution(
        config,
        scheduling_override=scheduling_override,
        workers_override=workers_override,
    )
    resolved_hermes = hermes_executable or resolve_hermes_executable()
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
        selected, resolved_scenarios = resolve_explicit_scenarios(questions, selection)
        validate_frozen_selection(selected, selection)
        samples_per_task = int(config["generation"]["samples_per_task"])
        selection_method = (
            "frozen category-grouped scenario IDs"
            if "scenarios" in selection
            else "frozen explicit question IDs; output-blind stratified shortlist"
        )
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
        resolved_scenarios = [
            {
                "id": str(question["question_id"]),
                "category": str(question.get("category")),
                "family": str(question.get("task")),
            }
            for question in selected
        ]
    execution_arms = list(config.get("execution_arms") or config["arms"])
    selected_pairs = make_pairs(
        selected, int(config["seed"]), samples_per_task, arms=execution_arms
    )

    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    configure_homes(config, source_home, run_dir / "homes")
    generated_homes = {arm: run_dir / "homes" / arm for arm in config["arms"]}
    hermes_compatibility = (
        probe_hermes_compatibility(config, generated_homes, executable=resolved_hermes)
        if config.get("compatibility")
        else {
            "status": "legacy-unvalidated",
            "reason": "historical config predates Hermes compatibility profiles",
            "executable": resolved_hermes,
            "warning_codes": ["LEGACY_UNVALIDATED_HERMES"],
            "warnings": [
                "historical config has no Hermes compatibility profile; behavior is unverified"
            ],
        }
    )
    for warning in hermes_compatibility.get("warnings", []):
        print(f"WARNING: {warning}", file=sys.stderr)
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
        "hermes_compatibility": hermes_compatibility,
        "selection": {
            "method": selection_method,
            "question_ids": [str(q["question_id"]) for q in selected],
            "scenarios": resolved_scenarios,
            "scenarios_sha256": sha256_bytes(canonical_json(resolved_scenarios)),
            "category_counts": {
                category: sum(q.get("category") == category for q in selected)
                for category in sorted({str(q.get("category")) for q in selected})
            },
            "family_counts": {
                category: {
                    family: sum(
                        q.get("category") == category and q.get("task") == family for q in selected
                    )
                    for family in sorted(
                        {str(q.get("task")) for q in selected if str(q.get("category")) == category}
                    )
                }
                for category in sorted({str(q.get("category")) for q in selected})
            },
        },
        "execution_contract": {
            "baseline_arm": config.get("execution", {}).get("baseline_arm", "base"),
            **execution,
            "retries": int(config.get("generation", {}).get("retries", 0)),
            "timeout_seconds": int(config.get("generation", {}).get("timeout_seconds", 900)),
            "order": (
                "seeded pair order; complete counterbalanced arm groups with wave barriers"
                if execution["scheduling"] == "balanced_waves"
                else "seeded pair order; counterbalanced arm submission without barriers"
            ),
            "timing_note": (
                None
                if execution["timing_comparable"]
                else "* non-strict streaming timing is not paired arm wall-time evidence"
            ),
        },
        "cell_journal_schema_version": 1,
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
    *,
    executable: str = "hermes",
) -> dict[str, Any]:
    turns: list[str] = []
    started = time.monotonic()
    for _ in question["turns"]:
        prompt = build_prompt(question, turns)
        command = build_command(arm_name, arm, prompt, executable=executable)
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
            raise CellExecutionError(
                f"{arm_name} failed rc={completed.returncode}: {completed.stderr[-2000:]}"
            )
        turns.append(validate_answer_output(arm_name, completed.stdout))
    return {
        "turns": turns,
        "total_time_s": round(time.monotonic() - started, 3),
        "stdout_sha256": sha256_bytes("\n".join(turns).encode()),
    }


def validate_answer_output(arm_name: str, output: str) -> str:
    text = output.strip()
    if not text:
        raise CellExecutionError(f"{arm_name} returned empty output")
    if text.casefold() == "(empty response)":
        raise CellExecutionError(f"{arm_name} returned degraded output")
    return text


def subprocess_environment(home: Path) -> dict[str, str]:
    secret_markers = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in secret_markers)
    }
    env["HERMES_HOME"] = str(home)
    return env


def parse_hermes_version(output: str) -> str:
    match = re.search(r"Hermes Agent v(\d+\.\d+\.\d+)", output)
    if not match:
        raise ContractError(f"unable to parse Hermes version from: {output.strip()!r}")
    return match.group(1)


def _probe_failure(
    arm_name: str,
    version: str,
    home: Path,
    command: list[str],
    stdout: str,
    stderr: str,
) -> ContractError:
    details = stderr.strip() or stdout.strip() or "command returned no diagnostic output"
    rendered = " ".join(command)
    return ContractError(
        f"Hermes compatibility check failed for arm '{arm_name}'\n"
        f"Hermes version: {version}\n"
        f"Generated config: {home / 'config.yaml'}\n"
        f"Command: HERMES_HOME={home} {rendered}\n"
        f"Hermes diagnostic:\n{details}"
    )


def _run_probe_command(
    runner,
    command: list[str],
    *,
    arm_name: str,
    version: str,
    home: Path,
):
    result = runner(
        command,
        text=True,
        capture_output=True,
        env=subprocess_environment(home),
        check=False,
    )
    if result.returncode != 0:
        raise _probe_failure(arm_name, version, home, command, result.stdout, result.stderr)
    return result


def probe_hermes_compatibility(
    config: dict[str, Any],
    homes: dict[str, Path],
    *,
    executable: str | None = None,
    runner=None,
) -> dict[str, Any]:
    profile = config.get("compatibility", {}).get("hermes", {}).get("profile")
    if profile not in SUPPORTED_HERMES_PROFILES:
        supported = ", ".join(sorted(SUPPORTED_HERMES_PROFILES))
        raise ContractError(f"unsupported Hermes compatibility profile; supported: {supported}")
    resolved = executable or shutil.which("hermes")
    if not resolved:
        raise ContractError("Hermes executable not found on PATH; install Hermes before prepare")
    command_runner = runner or subprocess.run
    version_result = command_runner(
        [resolved, "--version"], text=True, capture_output=True, check=False
    )
    if version_result.returncode != 0:
        diagnostic = version_result.stderr.strip() or version_result.stdout.strip()
        raise ContractError(f"failed to execute Hermes version probe: {diagnostic}")
    version_output = version_result.stdout + "\n" + version_result.stderr
    version = parse_hermes_version(version_output)
    if version != profile:
        warning = (
            f"Hermes version mismatch: expected profile {profile}, installed {version}; "
            "profile-specific compatibility probes were skipped and model calls may proceed "
            "with unverified Hermes behavior"
        )
        return {
            "status": "unverified-version",
            "profile": profile,
            "version": version,
            "executable": str(Path(resolved).resolve()),
            "version_line": version_output.strip().splitlines()[0],
            "warning_codes": ["HERMES_VERSION_MISMATCH"],
            "warnings": [warning],
            "arms": {},
        }

    arm_reports: dict[str, Any] = {}
    for arm_name, arm in config["arms"].items():
        home = homes[arm_name]
        validate_hermes_arm_schema(arm_name, arm, str(profile))
        config_check = [resolved, "config", "check"]
        _run_probe_command(
            command_runner,
            config_check,
            arm_name=arm_name,
            version=version,
            home=home,
        )
        hermes_cfg = arm_hermes_config(arm)
        expected: dict[str, Any] = {
            "model.provider": hermes_cfg["model"]["provider"],
            "model.default": hermes_cfg["model"]["default"],
            "agent.reasoning_effort": hermes_cfg["agent"]["reasoning_effort"],
            "moa.enabled": hermes_cfg["moa"]["enabled"],
        }
        if hermes_cfg["moa"]["enabled"]:
            expected["moa.active_preset"] = hermes_cfg["moa"]["active_preset"]
        effective: dict[str, Any] = {}
        for key, expected_value in expected.items():
            command = [resolved, "config", "get", key, "--json"]
            result = _run_probe_command(
                command_runner,
                command,
                arm_name=arm_name,
                version=version,
                home=home,
            )
            try:
                actual_value = json.loads(result.stdout)
            except json.JSONDecodeError as error:
                raise _probe_failure(
                    arm_name,
                    version,
                    home,
                    command,
                    result.stdout,
                    f"invalid JSON from Hermes config get: {error}",
                ) from error
            if actual_value != expected_value:
                raise ContractError(
                    f"Hermes effective config mismatch for arm '{arm_name}'\n"
                    f"Hermes version: {version}\n"
                    f"Generated config: {home / 'config.yaml'}\n"
                    f"Path: {key}\nExpected: {expected_value!r}\nActual: {actual_value!r}"
                )
            effective[key] = actual_value
        prompt_command = [resolved, "prompt-size", "--json"]
        prompt_result = _run_probe_command(
            command_runner,
            prompt_command,
            arm_name=arm_name,
            version=version,
            home=home,
        )
        try:
            prompt_report = json.loads(prompt_result.stdout)
        except json.JSONDecodeError as error:
            raise _probe_failure(
                arm_name,
                version,
                home,
                prompt_command,
                prompt_result.stdout,
                f"invalid JSON from Hermes prompt-size: {error}",
            ) from error
        arm_reports[arm_name] = {
            "config_check": "passed",
            "effective": effective,
            "prompt_size_sha256": sha256_bytes(canonical_json(prompt_report)),
            "tool_schema_count": int(prompt_report.get("tools", {}).get("count", 0)),
        }
    return {
        "status": "verified",
        "profile": profile,
        "version": version,
        "executable": str(Path(resolved).resolve()),
        "version_line": version_output.strip().splitlines()[0],
        "warning_codes": [],
        "warnings": [],
        "arms": arm_reports,
    }


def invoke_pair_parallel(
    arms: dict[str, dict[str, Any]],
    homes: dict[str, Path],
    question: dict[str, Any],
    timeout: int,
    *,
    executable: str = "hermes",
    invoke=invoke_arm,
) -> dict[str, dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=len(arms), thread_name_prefix="livebench-arm") as executor:
        futures = {
            arm_name: executor.submit(
                invoke,
                arm_name,
                arms[arm_name],
                homes[arm_name],
                question,
                timeout,
                executable=executable,
            )
            for arm_name in arms
        }
        return {arm_name: future.result() for arm_name, future in futures.items()}


def prepare_cell_home(run_dir: Path, arm_name: str, pair_id: str) -> Path:
    template = run_dir / "homes" / arm_name
    cell_home = run_dir / "cell-homes" / arm_name / pair_id
    if cell_home.exists():
        raise ContractError(f"cell Hermes home already exists: {cell_home}")
    cell_home.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copytree(template, cell_home, symlinks=True)
    trace_dir = cell_home / "moa-traces"
    if trace_dir.exists():
        shutil.rmtree(trace_dir)
    return cell_home


def collect_cell_traces(run_dir: Path, arm_name: str, pair_id: str, cell_home: Path) -> None:
    source = cell_home / "moa-traces"
    if not source.is_dir():
        return
    destination = run_dir / "homes" / arm_name / "moa-traces"
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for index, path in enumerate(sorted(source.glob("*.jsonl"))):
        shutil.copy2(path, destination / f"{pair_id}-{index}.jsonl")


def write_cell_outcome(run_dir: Path, outcome: dict[str, Any]) -> Path:
    arm_name = str(outcome["arm"])
    pair_id = str(outcome["pair_id"])
    directory = run_dir / "cells" / arm_name
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"{pair_id}.json"
    if path.exists():
        raise ContractError(f"cell outcome already exists: {path}")
    temporary = directory / f".{pair_id}.{threading.get_ident()}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(canonical_json(outcome) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def select_resume_cells(
    run_dir: Path,
    pairs: list[dict[str, Any]],
    arm_names: tuple[str, ...],
    *,
    retry_excluded: bool,
    arms: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    expected = {
        (arm, str(pair["pair_id"])): (str(pair["question_id"]), int(pair["sample_index"]))
        for pair in pairs
        for arm in arm_names
    }
    outcomes: dict[tuple[str, str], dict[str, Any]] = {}
    cells_dir = run_dir / "cells"
    for path in sorted(cells_dir.glob("*/*.json")) if cells_dir.is_dir() else []:
        try:
            outcome = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ContractError(f"malformed cell outcome {path}: {error.msg}") from error
        arm = str(outcome.get("arm"))
        pair_id = str(outcome.get("pair_id"))
        identity = (arm, pair_id)
        if identity not in expected:
            raise ContractError(f"cell outcome is outside frozen matrix: {path}")
        if path != cells_dir / arm / f"{pair_id}.json":
            raise ContractError(f"cell outcome path does not match identity: {path}")
        question_id, sample_index = expected[identity]
        if (
            str(outcome.get("question_id")) != question_id
            or int(outcome.get("sample_index", -1)) != sample_index
        ):
            raise ContractError(f"cell outcome identity does not match frozen matrix: {path}")
        if identity in outcomes:
            raise ContractError(f"duplicate cell outcome: {arm}/{pair_id}")
        status = outcome.get("status")
        if status == "valid":
            record = outcome.get("record") or {}
            if (
                str(record.get("question_id")) != question_id
                or int(record.get("sample_index", -1)) != sample_index
            ):
                raise ContractError(f"valid cell record identity mismatch: {path}")
            if str((record.get("api_info") or {}).get("pair_id")) != pair_id:
                raise ContractError(f"valid cell record pair_id mismatch: {path}")
        elif status == "excluded":
            if not str(outcome.get("code") or "") or not str(outcome.get("reason") or ""):
                raise ContractError(f"excluded cell is missing code or reason: {path}")
        else:
            raise ContractError(f"unsupported cell outcome status in {path}")
        outcomes[identity] = outcome

    selected: list[dict[str, Any]] = []
    for pair in pairs:
        order = tuple(pair.get("order") or arm_names)
        if len(order) != len(arm_names) or set(order) != set(arm_names):
            raise ContractError(f"pair order is not an exact arm permutation: {pair['pair_id']}")
        for arm_name in order:
            if arm_name not in arm_names:
                raise ContractError(f"pair order contains unknown arm: {arm_name}")
            key = (arm_name, str(pair["pair_id"]))
            outcome = outcomes.get(key)
            invalid_trace = False
            if (
                retry_excluded
                and outcome is not None
                and outcome.get("status") == "valid"
                and arms is not None
                and arm_reference_models(arms[arm_name])
            ):
                trace_dir = run_dir / "homes" / arm_name / "moa-traces"
                paths = sorted(trace_dir.glob(f"{pair['pair_id']}-*.jsonl"))
                try:
                    if len(paths) != 1:
                        raise ContractError(f"expected one trace, got {len(paths)}")
                    rows = [
                        json.loads(line)
                        for line in paths[0].read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                    if len(rows) != 1:
                        raise ContractError(f"expected one trace record, got {len(rows)}")
                    answer = str(outcome["record"]["choices"][0]["turns"][-1])
                    validate_moa_trace_record(rows[0], answer, arm_hermes_config(arms[arm_name]))
                except (
                    ContractError,
                    json.JSONDecodeError,
                    KeyError,
                    IndexError,
                    TypeError,
                    ValueError,
                ):
                    invalid_trace = True
            if (
                outcome is None
                or invalid_trace
                or (
                    retry_excluded
                    and outcome.get("status") == "excluded"
                    and outcome.get("code") in RETRYABLE_EXCLUSION_CODES
                )
            ):
                selected.append({**pair, "arm_name": arm_name})
    return selected


def archive_cell_attempt(run_dir: Path, cell: dict[str, Any]) -> int:
    arm_name = str(cell["arm_name"])
    pair_id = str(cell["pair_id"])
    attempt_dir = run_dir / "attempts" / arm_name / pair_id
    attempt_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    numbers = [int(path.name.split("-", 1)[0]) for path in attempt_dir.iterdir()]
    attempt = max(numbers, default=0) + 1
    destination = attempt_dir / f"{attempt:04d}-previous"
    destination.mkdir(mode=0o700)
    outcome_path = run_dir / "cells" / arm_name / f"{pair_id}.json"
    if outcome_path.exists():
        shutil.move(str(outcome_path), destination / "outcome.json")
    cell_home = run_dir / "cell-homes" / arm_name / pair_id
    if cell_home.exists():
        shutil.move(str(cell_home), destination / "cell-home")
    trace_dir = run_dir / "homes" / arm_name / "moa-traces"
    traces = sorted(trace_dir.glob(f"{pair_id}-*.jsonl")) if trace_dir.is_dir() else []
    if traces:
        archived_traces = destination / "moa-traces"
        archived_traces.mkdir(mode=0o700)
        for path in traces:
            shutil.move(str(path), archived_traces / path.name)
    return attempt


def cell_exclusion(cell: dict[str, Any], code: str, reason: str) -> dict[str, Any]:
    return {
        "status": "excluded",
        "arm": cell["arm_name"],
        "pair_id": cell["pair_id"],
        "question_id": cell["question_id"],
        "sample_index": cell["sample_index"],
        "code": code,
        "reason": reason,
    }


def finalize_outcomes(run_dir: Path, manifest: dict[str, Any], arm_names: tuple[str, ...]) -> None:
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True, mode=0o700)
    pair_position = {str(pair["pair_id"]): index for index, pair in enumerate(manifest["pairs"])}
    exclusions: list[dict[str, Any]] = []
    for arm_name in arm_names:
        directory = run_dir / "cells" / arm_name
        outcomes = (
            [
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(directory.glob("*.json"))
            ]
            if directory.is_dir()
            else []
        )
        if len(outcomes) != len(manifest["pairs"]):
            raise ContractError(
                f"cell outcome cardinality mismatch for {arm_name}: "
                f"expected {len(manifest['pairs'])}, got {len(outcomes)}"
            )
        seen: set[str] = set()
        valid_records: list[tuple[int, dict[str, Any]]] = []
        for outcome in outcomes:
            pair_id = str(outcome.get("pair_id"))
            if (
                pair_id not in pair_position
                or pair_id in seen
                or str(outcome.get("arm")) != arm_name
            ):
                raise ContractError(f"invalid or duplicate cell outcome for {arm_name}/{pair_id}")
            seen.add(pair_id)
            if outcome.get("status") == "valid":
                valid_records.append((pair_position[pair_id], outcome["record"]))
            elif outcome.get("status") == "excluded":
                exclusions.append({key: value for key, value in outcome.items() if key != "status"})
            else:
                raise ContractError(f"unsupported cell outcome status for {arm_name}/{pair_id}")
        payload = "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for _, record in sorted(valid_records, key=lambda item: item[0])
        )
        (raw_dir / f"hermes-{arm_name}.jsonl").write_text(payload, encoding="utf-8")
    (run_dir / "exclusions.json").write_bytes(
        canonical_json({"schema_version": 1, "excluded_cells": exclusions}) + b"\n"
    )


def execute_cells(
    config_path: Path,
    run_dir: Path,
    config: dict[str, Any],
    manifest: dict[str, Any],
    cells: list[dict[str, Any]],
    resolved_hermes: str,
    *,
    resumed: bool,
) -> None:
    if not cells:
        finalize_outcomes(run_dir, manifest, tuple(config["arms"]))
        return
    questions = json.loads((run_dir / "questions.json").read_text(encoding="utf-8"))
    by_id = {str(question["question_id"]): question for question in questions}
    execution = manifest["execution_contract"]
    scheduling = "streaming" if resumed else execution["scheduling"]
    workers = min(int(execution["effective_workers"]), len(cells))
    waves = (
        [cells]
        if scheduling == "streaming"
        else schedule_cells(
            manifest["pairs"], tuple(config["arms"]), scheduling=scheduling, workers=workers
        )
    )
    selected = {(str(cell["arm_name"]), str(cell["pair_id"])) for cell in cells}
    waves = [
        [cell for cell in wave if (str(cell["arm_name"]), str(cell["pair_id"])) in selected]
        for wave in waves
    ]
    waves = [wave for wave in waves if wave]
    run_started = time.monotonic()

    def execute_cell(cell: dict[str, Any], start_barrier: threading.Barrier | None):
        verify_run_integrity(config_path, run_dir, manifest)
        arm_name = str(cell["arm_name"])
        pair_id = str(cell["pair_id"])
        question = by_id[str(cell["question_id"])]
        if (run_dir / "cells" / arm_name / f"{pair_id}.json").exists():
            archive_cell_attempt(run_dir, cell)
        try:
            cell_home = prepare_cell_home(run_dir, arm_name, pair_id)
            if start_barrier is not None:
                start_barrier.wait(timeout=effective_timeout(config))
        except (ContractError, OSError, RuntimeError, threading.BrokenBarrierError):
            if start_barrier is not None:
                start_barrier.abort()
            raise
        cell_started = time.monotonic()
        try:
            result = invoke_arm(
                arm_name,
                config["arms"][arm_name],
                cell_home,
                question,
                effective_timeout(config),
                executable=resolved_hermes,
            )
        except subprocess.TimeoutExpired:
            collect_cell_traces(run_dir, arm_name, pair_id, cell_home)
            outcome = cell_exclusion(
                cell,
                "CELL_TIMEOUT",
                f"Hermes subprocess exceeded {effective_timeout(config)} seconds",
            )
            outcome["elapsed_seconds"] = round(time.monotonic() - cell_started, 3)
            write_cell_outcome(run_dir, outcome)
            return outcome
        except CellExecutionError as error:
            collect_cell_traces(run_dir, arm_name, pair_id, cell_home)
            outcome = cell_exclusion(cell, "MODEL_OR_PROVIDER_FAILURE", str(error)[-2000:])
            outcome["elapsed_seconds"] = round(time.monotonic() - cell_started, 3)
            write_cell_outcome(run_dir, outcome)
            return outcome
        collect_cell_traces(run_dir, arm_name, pair_id, cell_home)
        provider, model, reasoning = arm_identity(config["arms"][arm_name])
        record = {
            "question_id": question["question_id"],
            "answer_id": sha256_bytes(f"{pair_id}:{arm_name}".encode())[:16],
            "sample_index": cell["sample_index"],
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
                "pair_id": pair_id,
                "sample_index": cell["sample_index"],
                "response_sha256": result["stdout_sha256"],
            },
        }
        outcome = {
            "status": "valid",
            "arm": arm_name,
            "pair_id": pair_id,
            "question_id": question["question_id"],
            "sample_index": cell["sample_index"],
            "record": record,
        }
        write_cell_outcome(run_dir, outcome)
        return outcome

    for wave in waves:
        start_barrier = threading.Barrier(len(wave)) if scheduling == "balanced_waves" else None
        with ThreadPoolExecutor(
            max_workers=min(workers, len(wave)), thread_name_prefix="livebench-cell"
        ) as executor:
            futures = [executor.submit(execute_cell, cell, start_barrier) for cell in wave]
            for future in futures:
                future.result()
    finalize_outcomes(run_dir, manifest, tuple(config["arms"]))
    history = list(manifest.get("execution_attempts") or [])
    history.append(
        {
            "kind": "resume" if resumed else "initial",
            "executed_cells": len(cells),
            "makespan_seconds": round(time.monotonic() - run_started, 3),
            "timing_comparable": bool(execution["timing_comparable"] and not resumed),
        }
    )
    manifest["execution_attempts"] = history
    manifest["execution_result"] = {
        "run_makespan_seconds": round(sum(float(item["makespan_seconds"]) for item in history), 3),
        "timing_comparable": bool(execution["timing_comparable"] and len(history) == 1),
        "timing_note": (
            execution.get("timing_note")
            if len(history) == 1
            else "resumed execution is not one paired wall-time experiment"
        ),
    }
    (run_dir / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")


def run(
    config_path: Path,
    source_home: Path,
    run_dir: Path,
    hermes_executable: str | None = None,
    *,
    scheduling_override: str | None = None,
    workers_override: int | None = None,
) -> None:
    config = load_config(config_path)
    resolved_hermes = resolve_hermes_executable(hermes_executable)
    manifest = prepare(
        config_path,
        source_home,
        run_dir,
        resolved_hermes,
        scheduling_override=scheduling_override,
        workers_override=workers_override,
    )
    arm_names = tuple(config["arms"])
    cells = [
        {**pair, "arm_name": arm_name}
        for pair in manifest["pairs"]
        for arm_name in pair.get("order") or arm_names
    ]
    execute_cells(config_path, run_dir, config, manifest, cells, resolved_hermes, resumed=False)


def resume_run(
    config_path: Path,
    run_dir: Path,
    hermes_executable: str | None = None,
    *,
    retry_excluded: bool = False,
) -> None:
    config = load_config(config_path)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ContractError(f"missing run manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("cell_journal_schema_version") != 1:
        raise ContractError("run predates durable cell journals; automatic resume is unsafe")
    if manifest.get("arms") != config.get("arms"):
        raise ContractError("configured arms drift from frozen manifest")
    verify_run_integrity(config_path, run_dir, manifest)
    resolved_hermes = resolve_hermes_executable(hermes_executable)
    compatibility = probe_hermes_compatibility(
        config,
        {arm: run_dir / "homes" / arm for arm in config["arms"]},
        executable=resolved_hermes,
    )
    frozen = manifest.get("hermes_compatibility") or {}
    if compatibility != frozen:
        raise ContractError("Hermes compatibility provenance drift on resume")
    cells = select_resume_cells(
        run_dir,
        manifest["pairs"],
        tuple(config["arms"]),
        retry_excluded=retry_excluded,
        arms=config["arms"],
    )
    execute_cells(config_path, run_dir, config, manifest, cells, resolved_hermes, resumed=True)


def run_single_arm(
    config_path: Path,
    source_home: Path,
    run_dir: Path,
    arm_name: str,
    hermes_executable: str | None = None,
) -> None:
    config = load_config(config_path)
    if arm_name not in config["arms"]:
        raise ContractError(f"unknown arm: {arm_name}")
    resolved_hermes = resolve_hermes_executable(hermes_executable)
    manifest = prepare(config_path, source_home, run_dir, resolved_hermes)
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
            executable=resolved_hermes,
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
    p.add_argument(
        "--hermes-executable",
        type=Path,
        help="Exact Hermes binary to probe and use; overrides HERMES_EXECUTABLE and PATH",
    )
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="No-cost validation and manifest creation")
    prep.add_argument("--run-dir", type=Path, default=ROOT / "runs/smoke")
    prep.add_argument(
        "--workers", type=int, help="Worker threads (1-32; default: 4 x CPUs, capped at 32)"
    )
    prep.add_argument(
        "--balanced-waves",
        action="store_true",
        help="Use synchronized complete-arm waves for comparable wall-time evidence",
    )
    execute = sub.add_parser("run", help="Execute paid paired model calls")
    execute.add_argument("--run-dir", type=Path, default=ROOT / "runs/smoke")
    execute.add_argument(
        "--workers", type=int, help="Worker threads (1-32; default: 4 x CPUs, capped at 32)"
    )
    execute.add_argument(
        "--balanced-waves",
        action="store_true",
        help="Use synchronized complete-arm waves for comparable wall-time evidence",
    )

    resume = sub.add_parser(
        "resume", help="Continue only missing cells in an existing journaled run"
    )
    resume.add_argument("--run-dir", type=Path, required=True)
    resume.add_argument(
        "--retry-excluded",
        action="store_true",
        help=(
            "Also retry timeout, model/provider, and invalid-MoA-trace cells; may incur paid calls"
        ),
    )

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
            manifest = prepare(
                args.config,
                args.source_hermes_home,
                args.run_dir,
                resolve_hermes_executable(args.hermes_executable),
                scheduling_override="balanced_waves" if args.balanced_waves else None,
                workers_override=args.workers,
            )
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
        elif args.command == "run":
            run(
                args.config,
                args.source_hermes_home,
                args.run_dir,
                args.hermes_executable,
                scheduling_override="balanced_waves" if args.balanced_waves else None,
                workers_override=args.workers,
            )
        elif args.command == "resume":
            resume_run(
                args.config,
                args.run_dir,
                args.hermes_executable,
                retry_excluded=args.retry_excluded,
            )
        elif args.command == "run-arm":
            run_single_arm(
                args.config,
                args.source_hermes_home,
                args.run_dir,
                args.arm,
                args.hermes_executable,
            )
        else:
            from .scoring import score_run

            print(json.dumps(score_run(args.run_dir), indent=2, ensure_ascii=False))
    except (ContractError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
