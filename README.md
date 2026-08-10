# LiveBench Hermes A/B

Paired evaluation project comparing:

- **BASE:** Hermes Agent with `openai-codex:gpt-5.6-sol`, reasoning `low`.
- **MoA:** Hermes preset `default`: the same `gpt-5.6-sol low` aggregator plus `openrouter:minimax/minimax-m3`.

Prompts, questions, turn handling, output limits, arm order policy, and objective scoring are shared. Only MoA reference context changes.

LiveBench is pinned in [`upstream`](upstream) at commit `00eae856aa1c1a9e9d058a65a9a94d85884034c4`.

## Setup

The repository is already prepared. To recreate the environment and public question data:

```bash
uv sync --extra test --extra livebench
PYTHONPATH=upstream uv run --extra livebench python upstream/livebench/download_questions.py
NLTK_DATA=$HOME/.cache/nltk_data uv run --extra livebench python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
uv run livebench-hermes-ab prepare --run-dir runs/smoke
```

`prepare` makes no model calls. It verifies the upstream SHA, freezes question/config hashes, creates isolated Hermes homes, and writes `runs/smoke/manifest.json`.

The smoke selection is blind and deterministic: one demanding question each from math, reasoning, data analysis, language, and instruction following.

## Run

```bash
uv run livebench-hermes-ab run --run-dir runs/smoke
```

The five-question smoke performs:

- 5 BASE calls;
- 5 Minimax reference calls;
- 5 MoA aggregator calls;
- 15 model calls total.

`every_n:3` refreshes references on the first iteration of every user turn; tools are disabled, so each one-turn question gets exactly one reference fanout.

The run also requires five full MoA traces. It fails closed unless each Minimax reference is non-empty, has positive token usage, and each aggregator output hash-matches its saved answer.

Use a fresh run directory for every execution. Existing answer files are rejected to prevent duplicate or mixed pairs.

## Score

```bash
uv run livebench-hermes-ab score --run-dir runs/smoke
uv run python scripts/build_report.py --run runs/smoke --output reports
```

Scoring is local and deterministic. The wrapper lazy-loads the task-specific processors from the pinned LiveBench checkout and makes no judge-model calls.

Outputs:

```text
runs/smoke/raw/hermes-base.jsonl
runs/smoke/raw/hermes-moa.jsonl
runs/smoke/scores.json
runs/smoke/summary.json
```

## Isolation

Each arm receives an isolated `HERMES_HOME` and runs with `--ignore-rules`. Every built-in toolset is disabled in the isolated config; offline `hermes prompt-size --json` must report zero tool schemas.

- Both arms use the existing OpenAI Codex OAuth `auth.json` through a read-only symlink.
- BASE receives an empty `.env` and cannot access OpenRouter credentials.
- MoA receives a private `0600` `.env` containing only `OPENROUTER_API_KEY`.
- Telegram, GitHub, memory, skills, repository instructions, tools, and unrelated credentials are excluded.
- `runs/`, `data/`, credentials, and generated answers are ignored by Git.

## Fail-closed gates

- Exact upstream commit and experiment hashes.
- BASE and MoA aggregator must match provider/model/reasoning.
- Minimax M3 is the only reference model.
- `degraded_reference_policy: loud` rejects failed references.
- Full MoA traces prove exact reference cardinality, model identity, positive usage, and aggregator-output matching.
- Stable pair IDs and alternating arm order.
- Byte-identical prompt construction across arms.
- Incomplete or duplicate answer cells cannot be scored.
