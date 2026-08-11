#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RUNTIME_DIR=${HERMES_RUNTIME_DIR:-"$ROOT/.hermes-runtime/hermes-agent"}
REPO_URL=https://github.com/NousResearch/hermes-agent.git
COMMIT=dac4bbea09a342879d9769d6a5357b12b84b936c
EXPECTED_VERSION=0.19.1

if [[ -e "$RUNTIME_DIR" && ! -d "$RUNTIME_DIR/.git" ]]; then
  printf 'ERROR: runtime path exists but is not a Hermes Git checkout: %s\n' "$RUNTIME_DIR" >&2
  exit 1
fi

if [[ ! -d "$RUNTIME_DIR/.git" ]]; then
  mkdir -p "$(dirname "$RUNTIME_DIR")"
  git clone --filter=blob:none "$REPO_URL" "$RUNTIME_DIR"
else
  origin=$(git -C "$RUNTIME_DIR" remote get-url origin)
  if [[ "$origin" != "$REPO_URL" ]]; then
    printf 'ERROR: unexpected Hermes runtime origin: %s\n' "$origin" >&2
    exit 1
  fi
  if [[ -n "$(git -C "$RUNTIME_DIR" status --porcelain --untracked-files=no)" ]]; then
    printf 'ERROR: Hermes runtime has tracked local changes: %s\n' "$RUNTIME_DIR" >&2
    exit 1
  fi
fi

git -C "$RUNTIME_DIR" fetch --no-tags origin "$COMMIT"
git -C "$RUNTIME_DIR" checkout --detach "$COMMIT"
actual_commit=$(git -C "$RUNTIME_DIR" rev-parse HEAD)
if [[ "$actual_commit" != "$COMMIT" ]]; then
  printf 'ERROR: expected Hermes commit %s, got %s\n' "$COMMIT" "$actual_commit" >&2
  exit 1
fi

uv sync --locked --no-dev --directory "$RUNTIME_DIR"
executable="$RUNTIME_DIR/.venv/bin/hermes"
version_output=$("$executable" --version)
if [[ "$version_output" != Hermes\ Agent\ v"$EXPECTED_VERSION"* ]]; then
  printf 'ERROR: expected Hermes %s, got:\n%s\n' "$EXPECTED_VERSION" "$version_output" >&2
  exit 1
fi

printf 'Hermes runtime ready.\n'
printf 'Commit: %s\n' "$COMMIT"
printf 'Executable: %s\n' "$executable"
printf '\nUse it with:\n'
printf '  uv run livebench-hermes-ab --config config.yaml --hermes-executable %q prepare --run-dir runs/default\n' "$executable"
