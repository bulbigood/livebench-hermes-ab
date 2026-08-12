from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class PaidSmokeBlocked(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PaidSmokePreflight:
    task_id: str
    provider: str
    model: str
    max_turns: int
    max_cost_usd: float
    artifact_destination: Path


def load_paid_smoke_preflight(path: Path) -> PaidSmokePreflight:
    raw = yaml.safe_load(path.read_text())
    required = {
        "schema_version",
        "enabled",
        "identity_status",
        "scope",
        "model",
        "limits",
        "image",
        "artifacts",
        "approval",
    }
    if not isinstance(raw, dict) or set(raw) != required or raw["schema_version"] != 1:
        raise PaidSmokeBlocked("invalid paid-smoke preflight schema")
    blockers = []
    if not raw["enabled"]:
        blockers.append("disabled")
    if raw["identity_status"] != "confirmed_gated_livebench":
        blockers.append("gated identity unconfirmed")
    if not raw["approval"].get("granted"):
        blockers.append("operator approval missing")
    provider = raw["model"].get("provider")
    model = raw["model"].get("model")
    if not provider or not model:
        blockers.append("provider/model unset")
    scope = raw["scope"]
    if scope.get("arm") != "plain" or scope.get("samples") != 1:
        blockers.append("scope is not one plain sample")
    if blockers:
        raise PaidSmokeBlocked("; ".join(blockers))
    return PaidSmokePreflight(
        scope["task_id"],
        provider,
        model,
        raw["limits"]["max_turns"],
        float(raw["limits"]["max_cost_usd"]),
        Path(raw["artifacts"]["destination"]),
    )
