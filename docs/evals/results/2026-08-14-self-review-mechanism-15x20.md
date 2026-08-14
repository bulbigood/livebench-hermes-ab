# LiveBench Hermes experiment

## Corrected executive conclusion

This report supersedes the earlier calculation from the same immutable 15-scenario × 20-sample run. The earlier scorer treated 64 terminal provider failures as valid model answers because Hermes returned the failure text with exit code `0`. The corrected scorer excludes these outputs before constructing the common-valid paired cohort.

- Exact terminal failures: 64 (`base`: 35, `base_self_review`: 29, `moa_neutral`: 0).
- Other exclusions: five invalid `moa_neutral` traces.
- Correct common-valid coverage: 256/300 pairs. Forty-one pairs contain at least one terminal failure; five contain an invalid trace; two satisfy both conditions.
- Complete-case means: `base_self_review` 0.8738, `base` 0.8620, `moa_neutral` 0.8308.
- Complete-case contrasts: self-review−base +0.0117 (95% CI [−0.0126, +0.0360]); neutral−self-review −0.0430 ([−0.0703, −0.0156]); neutral−base −0.0312 ([−0.0581, −0.0043]).

These are **diagnostic complete-case estimates**, not a balanced confirmatory comparison over the preregistered target. Missingness is strongly scenario-dependent: one frozen olympiad scenario has zero retained pairs and another has only 2/20. The confidence intervals are conditional on the 256 surviving pairs and do not account for scenario-level clustering or non-random omission. Worst-case missing-data bounds below include zero for every planned contrast. Consequently, this report does not establish a broad quality ordering among the three policies.

Operationally, the run does establish a serious reliability difference: the plain acting path surfaced terminal provider errors as answers while the neutral aggregator path did not. That reliability defect must be repaired and affected cells recovered under frozen identities before a balanced quality comparison is attempted.

### Old → corrected headline values

| Metric | Earlier report | Corrected complete-case report |
|---|---:|---:|
| Common-valid pairs | 295/300 | 256/300 |
| `base` mean | 0.7705 | 0.8620 |
| `base_self_review` mean | 0.7954 | 0.8738 |
| `moa_neutral` mean | 0.8290 | 0.8308 |
| Self-review−base | +0.0248 [−0.0084, +0.0581] | +0.0117 [−0.0126, +0.0360] |
| Neutral−self-review | +0.0337 [−0.0037, +0.0711] | −0.0430 [−0.0703, −0.0156] |
| Neutral−base | +0.0585 [+0.0204, +0.0966] | −0.0312 [−0.0581, −0.0043] |
| Self-review−base harm / catastrophic | 13.6% / 3.7% | 13.3% / 2.0% |
| Neutral−self-review harm / catastrophic | 30.2% / 3.7% | 30.9% / 4.3% |
| Neutral−base harm / catastrophic | 27.8% / 3.4% | 29.7% / 3.9% |
| Minimum retained samples in any frozen scenario | Previously reported above zero | 0 |

Corrected scoring generation: `646097d5d7e44c9991b83d62354156a5`.

Common paired coverage: 256/300

| Arm | Mean | Median |
|---|---:|---:|
| base | 0.8620 | 0.9167 |
| base_self_review | 0.8738 | 0.9355 |
| moa_neutral | 0.8308 | 0.9167 |

## Run provenance

Hermes source: `/home/dev/projects/hermes-moa-critic-0191`
Observed Hermes: `0.19.1`

<details>
<summary>Frozen run configuration</summary>

```yaml
experiment:
  id: livebench-hermes-self-review-mechanism-15x10-v1
  upstream_commit: 00eae856aa1c1a9e9d058a65a9a94d85884034c4
  release: '2026-06-25'
  seed: 5615
  question_globs:
  - data/live_bench/*/*/question.jsonl
selection:
  scenarios:
    instruction_following:
    - id: 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5
      family: paraphrase
    math:
    - id: a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576
      family: math_comp
    - id: 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594
      family: olympiad
    - id: 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115
      family: olympiad
    - id: e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178
      family: olympiad
    - id: 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4
      family: olympiad
    - id: 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536
      family: olympiad
    - id: 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7
      family: olympiad
    - id: 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421
      family: olympiad
    data_analysis:
    - id: d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985
      family: tablejoin
    - id: a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48
      family: tablejoin
    - id: 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300
      family: tablejoin
    - id: d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551
      family: cta
    - id: 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c
      family: tablejoin
    - id: d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1
      family: tablejoin
generation:
  samples_per_task: 20
  retry:
    max_attempts: 2
    retryable_codes: []
execution:
  mode: streaming
  workers: auto
  timeout_seconds: 1800
  baseline_arm: base
compatibility:
  hermes:
    directory: /home/dev/projects/hermes-moa-critic-0191
arms:
  base:
    credential_env: []
    hermes:
      model:
        provider: openai-codex
        default: gpt-5.6-sol
      agent:
        reasoning_effort: low
        disabled_toolsets: &id001
        - web
        - browser
        - terminal
        - file
        - code_execution
        - vision
        - video
        - image_gen
        - video_gen
        - bfl
        - x_search
        - tts
        - stt
        - skills
        - todo
        - memory
        - context_engine
        - session_search
        - clarify
        - delegation
        - cronjob
        - homeassistant
        - spotify
        - yuanbao
        - computer_use
      moa:
        enabled: false
        save_traces: false
  base_self_review:
    credential_env: []
    hermes:
      model:
        provider: openai-codex
        default: gpt-5.6-sol
      agent:
        reasoning_effort: low
        disabled_toolsets: *id001
        system_prompt: 'Before finalizing each answer, silently perform this review:

          1. Confirm that the answer addresses the task actually asked.

          2. Check every material assumption against the available evidence.

          3. Derive and enforce all mechanically checkable output constraints.

          4. Distinguish supported conclusions from uncertainty; never turn a guess
          into a fact.

          5. Resolve contradictions using primary evidence and valid derivation, not
          confidence or repetition.

          If evidence is insufficient, preserve the uncertainty or obtain the missing
          evidence. Do not mention this private review to the user.'
      moa:
        enabled: false
        save_traces: false
  moa_neutral:
    credential_env:
    - OPENROUTER_API_KEY
    hermes:
      model:
        provider: moa
        default: default
      agent:
        disabled_toolsets: *id001
      moa:
        enabled: true
        default_preset: default
        active_preset: default
        save_traces: true
        presets:
          default:
            enabled: true
            advisory_prompt: neutral
            degraded_reference_policy: loud
            reference_max_tokens: 50000
            max_tokens: 4096
            fanout: every_n:3
            reference_models:
            - provider: openrouter
              model: xiaomi/mimo-v2.5
            aggregator:
              provider: openai-codex
              model: gpt-5.6-sol
              reasoning_effort: low
scoring:
  implementation: livebench-objective-ground-truth
  schema_version: 2
  confidence_level: 0.95
  target_margin_of_error: 0.03
  contrasts:
  - - base_self_review
    - base
  - - moa_neutral
    - base_self_review
  - - moa_neutral
    - base
```

</details>

## Exclusions

- INVALID_MOA_TRACE: 5
- MODEL_OR_PROVIDER_FAILURE: 64

## Sampling

| Configured samples/task | Minimum common-valid samples/task | Recommended samples/task |
|---:|---:|---:|
| 20 | 0 | Unavailable |

> WARNING: fewer than 5 common-valid samples per task; variance-based planning estimates are unstable.

## Paired better/worse decision analysis

The verdict uses a two-sided 95% confidence interval for common-valid paired score differences. Sample projections assume the observed effect and paired-difference variance persist; they are planning estimates, not guarantees.
Catastrophic harm means a paired score delta `<= -0.5`.

| Candidate vs baseline | n | Mean delta | Median delta | Harm rate | Catastrophic harm rate | 95% CI | Verdict | Projected CI-excluding-zero samples/scenario | 95% power samples/scenario |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| base_self_review vs base | 256 | 0.0117 | 0.0000 | 13.3% | 2.0% | [-0.0126, 0.0360] | inconclusive | 79 | 267 |
| moa_neutral vs base | 256 | -0.0312 | 0.0000 | 29.7% | 3.9% | [-0.0581, -0.0043] | worse | 14 | 46 |

## Planned paired contrasts

These contrasts were frozen in the experiment configuration before scoring.

| Contrast | n | Mean delta | Median delta | Harm rate | Catastrophic harm rate | 95% CI | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| base_self_review vs base | 256 | 0.0117 | 0.0000 | 13.3% | 2.0% | [-0.0126, 0.0360] | inconclusive |
| moa_neutral vs base_self_review | 256 | -0.0430 | 0.0000 | 30.9% | 4.3% | [-0.0703, -0.0156] | worse |
| moa_neutral vs base | 256 | -0.0312 | 0.0000 | 29.7% | 3.9% | [-0.0581, -0.0043] | worse |

## Missing-data sensitivity

The score and confidence-interval tables above are complete-case estimates conditional on every arm returning a valid output. Missingness is not assumed random. The bounds below assign every missing paired delta its worst possible value under the stated `[0, 1]` score range.

| Contrast | Observed pairs | Missing pairs | Worst-case mean-delta bounds |
|---|---:|---:|---:|
| base_self_review_vs_base | 256 | 44 | [-0.1367, 0.1567] |
| moa_neutral_vs_base_self_review | 256 | 44 | [-0.1833, 0.1100] |
| moa_neutral_vs_base | 256 | 44 | [-0.1733, 0.1200] |

## Score by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 20 | 0.8935 | 0.9032 | 0.9677 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base_self_review | 20 | 0.9008 | 0.9032 | 0.9677 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral | 20 | 0.8073 | 0.8387 | 0.9355 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 0 | — | — | — | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | base_self_review | 0 | — | — | — | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral | 0 | — | — | — | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | base | 17 | 0.8605 | 0.8710 | 0.9419 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base_self_review | 17 | 0.8975 | 0.9032 | 0.9677 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral | 17 | 0.6983 | 0.7258 | 0.8258 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base | 19 | 0.9013 | 0.9167 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | base_self_review | 19 | 0.8925 | 0.9167 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral | 19 | 0.8618 | 0.8750 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base | 20 | 1.0000 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | base_self_review | 20 | 1.0000 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral | 20 | 0.8935 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base | 20 | 0.9042 | 0.9167 | 0.9167 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | base_self_review | 20 | 0.9083 | 0.9167 | 0.9167 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral | 20 | 0.8979 | 0.9167 | 0.9167 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base | 20 | 0.9390 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | base_self_review | 20 | 0.9750 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral | 20 | 0.9140 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base | 2 | 0.9681 | 0.9681 | 0.9968 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | base_self_review | 2 | 0.9681 | 0.9681 | 0.9968 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral | 2 | 0.8723 | 0.8723 | 0.9298 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base | 20 | 0.9700 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | base_self_review | 20 | 0.9400 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base | 19 | 0.8226 | 0.8300 | 0.9100 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | base_self_review | 19 | 0.8353 | 0.8300 | 0.9100 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral | 19 | 0.8479 | 0.8300 | 0.9100 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base | 20 | 1.0000 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | base_self_review | 20 | 0.9500 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base | 20 | 0.1500 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | base_self_review | 20 | 0.3000 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral | 20 | 0.3000 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base | 20 | 0.8000 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base_self_review | 20 | 0.8000 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral | 20 | 0.6410 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base | 20 | 1.0000 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | base_self_review | 20 | 1.0000 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral | 20 | 0.9680 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base | 19 | 0.9592 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | base_self_review | 19 | 0.9566 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral | 19 | 0.9553 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Paired score deltas by scenario

Positive values favor the candidate over `base`.

| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base_self_review−base | 20 | 0.0073 | 0.0000 | 0.0984 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral−base | 20 | -0.0863 | -0.0806 | 0.0508 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base_self_review−base | 0 | — | — | — | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral−base | 0 | — | — | — | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | base_self_review−base | 17 | 0.0370 | 0.0323 | 0.1355 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral−base | 17 | -0.1622 | -0.1290 | -0.0097 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base_self_review−base | 19 | -0.0088 | 0.0000 | 0.0833 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral−base | 19 | -0.0395 | -0.0417 | 0.0458 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base_self_review−base | 20 | 0.0000 | 0.0000 | 0.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral−base | 20 | -0.1065 | 0.0000 | 0.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base_self_review−base | 20 | 0.0042 | 0.0000 | 0.0417 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral−base | 20 | -0.0062 | 0.0000 | 0.0417 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base_self_review−base | 20 | 0.0360 | 0.0000 | 0.5000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral−base | 20 | -0.0250 | 0.0000 | 0.1295 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base_self_review−base | 2 | 0.0000 | 0.0000 | 0.0000 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral−base | 2 | -0.0957 | -0.0957 | -0.0670 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base_self_review−base | 20 | -0.0300 | 0.0000 | 0.0300 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral−base | 20 | 0.0300 | 0.0000 | 0.0300 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base_self_review−base | 19 | 0.0126 | 0.0000 | 0.0860 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral−base | 19 | 0.0253 | 0.0600 | 0.0800 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base_self_review−base | 20 | -0.0500 | 0.0000 | 0.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral−base | 20 | 0.0000 | 0.0000 | 0.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base_self_review−base | 20 | 0.1500 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral−base | 20 | 0.1500 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base_self_review−base | 20 | 0.0000 | 0.0000 | 0.0000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral−base | 20 | -0.1590 | 0.0000 | 0.0000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base_self_review−base | 20 | 0.0000 | 0.0000 | 0.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral−base | 20 | -0.0320 | 0.0000 | 0.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base_self_review−base | 19 | -0.0026 | 0.0000 | 0.0500 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral−base | 19 | -0.0039 | 0.0000 | 0.0525 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Score by family

| Family | Scenarios | Arm | n | Mean | Median | p95 |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base | 20 | 0.1500 | 0.0000 | 1.0000 |
| cta | 1 | base_self_review | 20 | 0.3000 | 0.0000 | 1.0000 |
| cta | 1 | moa_neutral | 20 | 0.3000 | 0.0000 | 1.0000 |
| math_comp | 1 | base | 20 | 1.0000 | 1.0000 | 1.0000 |
| math_comp | 1 | base_self_review | 20 | 0.9500 | 1.0000 | 1.0000 |
| math_comp | 1 | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 |
| olympiad | 7 | base | 97 | 0.9059 | 0.9167 | 0.9742 |
| olympiad | 7 | base_self_review | 97 | 0.9125 | 0.9167 | 0.9677 |
| olympiad | 7 | moa_neutral | 97 | 0.8479 | 0.8750 | 0.9800 |
| paraphrase | 1 | base | 20 | 0.9700 | 1.0000 | 1.0000 |
| paraphrase | 1 | base_self_review | 20 | 0.9400 | 1.0000 | 1.0000 |
| paraphrase | 1 | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 |
| tablejoin | 5 | base | 99 | 0.9132 | 1.0000 | 1.0000 |
| tablejoin | 5 | base_self_review | 99 | 0.9229 | 1.0000 | 1.0000 |
| tablejoin | 5 | moa_neutral | 99 | 0.8529 | 0.9100 | 1.0000 |

## Paired score deltas by family

Positive values favor the candidate over `base`.

| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base_self_review−base | 20 | 0.1500 | 0.0000 | 1.0000 |
| cta | 1 | moa_neutral−base | 20 | 0.1500 | 0.0000 | 1.0000 |
| math_comp | 1 | base_self_review−base | 20 | -0.0500 | 0.0000 | 0.0000 |
| math_comp | 1 | moa_neutral−base | 20 | 0.0000 | 0.0000 | 0.0000 |
| olympiad | 7 | base_self_review−base | 97 | 0.0066 | 0.0000 | 0.0860 |
| olympiad | 7 | moa_neutral−base | 97 | -0.0580 | -0.0323 | 0.0500 |
| paraphrase | 1 | base_self_review−base | 20 | -0.0300 | 0.0000 | 0.0300 |
| paraphrase | 1 | moa_neutral−base | 20 | 0.0300 | 0.0000 | 0.0300 |
| tablejoin | 5 | base_self_review−base | 99 | 0.0097 | 0.0000 | 0.0800 |
| tablejoin | 5 | moa_neutral−base | 99 | -0.0603 | 0.0000 | 0.0800 |

## Overall wall time

Common-valid paired cells; values are seconds.

| Arm | n | Mean | Median | p95 |
|---|---:|---:|---:|---:|
| base | 256 | 35.8972 | 23.5394 | 85.8896 |
| base_self_review | 256 | 36.7649 | 24.2234 | 85.1210 |
| moa_neutral | 256 | 188.9404 | 114.0005 | 470.5831 |

### Paired overall wall-time deltas

Positive values mean the candidate is slower than `base`.

| Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---:|---:|---:|
| base_self_review−base | 256 | 0.8677 | 0.2518 | 21.0065 |
| moa_neutral−base | 256 | 153.0432 | 102.1237 | 392.5149 |

## Wall time by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 20 | 79.4115 | 73.7737 | 95.4006 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base_self_review | 20 | 77.9193 | 77.5887 | 88.8016 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral | 20 | 401.8467 | 370.3435 | 638.4699 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 17 | 108.7791 | 83.7320 | 178.2692 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base_self_review | 17 | 103.9804 | 83.7122 | 202.4440 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral | 17 | 399.4307 | 403.7782 | 515.2978 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base | 19 | 42.8498 | 41.3225 | 62.7137 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | base_self_review | 19 | 44.8608 | 44.1212 | 60.6256 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral | 19 | 332.3169 | 323.6587 | 452.2774 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base | 20 | 11.8680 | 11.9711 | 14.7298 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | base_self_review | 20 | 11.4913 | 10.6636 | 17.8175 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral | 20 | 84.3998 | 86.7206 | 126.5115 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base | 20 | 45.6519 | 43.8971 | 59.3705 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | base_self_review | 20 | 46.9614 | 46.8339 | 60.0775 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral | 20 | 344.0951 | 334.0986 | 498.4988 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base | 20 | 20.3457 | 18.6291 | 32.4224 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | base_self_review | 20 | 20.3775 | 20.2532 | 29.1830 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral | 20 | 87.9879 | 96.7032 | 148.1749 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base | 2 | 76.4727 | 76.4727 | 84.7639 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | base_self_review | 2 | 133.8032 | 133.8032 | 177.7150 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral | 2 | 392.4210 | 392.4210 | 426.1648 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base | 20 | 16.7089 | 16.9115 | 20.5140 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | base_self_review | 20 | 17.1500 | 16.2954 | 22.1138 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral | 20 | 40.4373 | 33.7790 | 68.1683 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base | 19 | 19.3629 | 14.8434 | 38.9593 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | base_self_review | 19 | 22.0973 | 21.9407 | 30.5208 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral | 19 | 54.1717 | 58.1835 | 76.0537 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base | 20 | 24.6759 | 24.3037 | 30.9431 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | base_self_review | 20 | 22.0641 | 22.6504 | 27.9559 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral | 20 | 200.1272 | 194.5555 | 269.3268 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base | 20 | 9.4286 | 9.1637 | 12.9282 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | base_self_review | 20 | 9.5505 | 8.9189 | 14.6291 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral | 20 | 48.1278 | 50.2589 | 67.6902 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base | 20 | 35.5304 | 30.5708 | 63.3569 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base_self_review | 20 | 35.2308 | 30.7713 | 63.4328 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral | 20 | 79.8619 | 72.7823 | 142.0654 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base | 20 | 6.3633 | 6.0946 | 10.4552 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | base_self_review | 20 | 7.6543 | 7.0797 | 12.1572 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral | 20 | 44.2375 | 43.5784 | 66.8508 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base | 19 | 52.9352 | 50.3234 | 71.7711 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | base_self_review | 19 | 59.8084 | 52.0969 | 91.8820 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral | 19 | 359.3611 | 344.7182 | 523.6181 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Paired wall-time deltas by scenario

Positive values mean the candidate is slower than `base`.

| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base_self_review−base | 20 | -1.4922 | -0.6307 | 16.5448 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral−base | 20 | 322.4352 | 289.6319 | 555.0064 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base_self_review−base | 17 | -4.7987 | -3.6579 | 96.0249 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral−base | 17 | 290.6515 | 290.5180 | 395.4764 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base_self_review−base | 19 | 2.0110 | 2.7987 | 19.5927 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral−base | 19 | 289.4671 | 285.4087 | 419.2072 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base_self_review−base | 20 | -0.3767 | -0.2203 | 4.6959 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral−base | 20 | 72.5318 | 73.8498 | 116.6593 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base_self_review−base | 20 | 1.3095 | 2.2001 | 15.2384 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral−base | 20 | 298.4432 | 287.4287 | 450.7595 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base_self_review−base | 20 | 0.0318 | 1.2743 | 14.6138 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 67.6422 | 79.2248 | 129.8089 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base_self_review−base | 2 | 57.3305 | 57.3305 | 109.5335 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral−base | 2 | 315.9483 | 315.9483 | 341.4009 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base_self_review−base | 20 | 0.4411 | -0.3487 | 5.4221 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral−base | 20 | 23.7284 | 18.4072 | 49.4629 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base_self_review−base | 19 | 2.7344 | 3.5914 | 20.9183 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral−base | 19 | 34.8088 | 38.1444 | 57.2184 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base_self_review−base | 20 | -2.6117 | -1.8261 | 5.2430 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral−base | 20 | 175.4514 | 167.7267 | 244.3434 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base_self_review−base | 20 | 0.1218 | -0.3263 | 4.2560 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral−base | 20 | 38.6992 | 38.9796 | 59.1012 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base_self_review−base | 20 | -0.2996 | 5.3172 | 21.2092 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 44.3316 | 42.4950 | 121.0977 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base_self_review−base | 20 | 1.2909 | 0.3684 | 7.7693 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 37.8741 | 36.2703 | 62.3337 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base_self_review−base | 19 | 6.8732 | 5.1651 | 30.8838 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral−base | 19 | 306.4259 | 284.2246 | 484.2121 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Wall time by family

| Family | Scenarios | Arm | n | Mean | Median | p95 |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base | 20 | 9.4286 | 9.1637 | 12.9282 |
| cta | 1 | base_self_review | 20 | 9.5505 | 8.9189 | 14.6291 |
| cta | 1 | moa_neutral | 20 | 48.1278 | 50.2589 | 67.6902 |
| math_comp | 1 | base | 20 | 24.6759 | 24.3037 | 30.9431 |
| math_comp | 1 | base_self_review | 20 | 22.0641 | 22.6504 | 27.9559 |
| math_comp | 1 | moa_neutral | 20 | 200.1272 | 194.5555 | 269.3268 |
| olympiad | 6 | base | 97 | 65.1894 | 55.5806 | 167.5358 |
| olympiad | 6 | base_self_review | 97 | 67.2330 | 59.5716 | 98.2906 |
| olympiad | 6 | moa_neutral | 97 | 367.3802 | 350.3183 | 554.9862 |
| paraphrase | 1 | base | 20 | 16.7089 | 16.9115 | 20.5140 |
| paraphrase | 1 | base_self_review | 20 | 17.1500 | 16.2954 | 22.1138 |
| paraphrase | 1 | moa_neutral | 20 | 40.4373 | 33.7790 | 68.1683 |
| tablejoin | 5 | base | 99 | 18.6873 | 13.9736 | 45.8211 |
| tablejoin | 5 | base_self_review | 99 | 19.3427 | 17.1222 | 41.1434 |
| tablejoin | 5 | moa_neutral | 99 | 70.2930 | 66.4202 | 137.9628 |

## Paired wall-time deltas by family

Positive values mean the candidate is slower than `base`.

| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base_self_review−base | 20 | 0.1218 | -0.3263 | 4.2560 |
| cta | 1 | moa_neutral−base | 20 | 38.6992 | 38.9796 | 59.1012 |
| math_comp | 1 | base_self_review−base | 20 | -2.6117 | -1.8261 | 5.2430 |
| math_comp | 1 | moa_neutral−base | 20 | 175.4514 | 167.7267 | 244.3434 |
| olympiad | 6 | base_self_review−base | 97 | 2.0436 | 2.2677 | 32.4826 |
| olympiad | 6 | moa_neutral−base | 97 | 302.1908 | 287.6677 | 478.9462 |
| paraphrase | 1 | base_self_review−base | 20 | 0.4411 | -0.3487 | 5.4221 |
| paraphrase | 1 | moa_neutral−base | 20 | 23.7284 | 18.4072 | 49.4629 |
| tablejoin | 5 | base_self_review−base | 99 | 0.6554 | 0.7054 | 17.4720 |
| tablejoin | 5 | moa_neutral−base | 99 | 51.6057 | 47.9706 | 122.2390 |

## Mechanism proxies

candidate adoption is normalized substring matching; erroneous/useful adoption uses the objective candidate score and is not claim-level semantic annotation

| Arm | Trace cells | Reference outputs | Candidate present | Candidate scorable | Candidate score mean | Exact adoption | Useful adoption | Erroneous adoption | Structural violations | Underdetermination signals | Wrapper present |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| moa_neutral | 295 | 295 | 2 | 2 | 0.1750 | 0 | 0 | 0 | 0 | 1 | 0 |

## Provider usage and billing completeness

- Evidence source: attempts
- Complete: False
- Recorded calls: 1200
- Cells/attempts without a provider ledger: 0
- Usage-complete calls: 300
- Cost-complete calls: 299
- Calls with provider generation IDs: 0

| Arm | Role | Provider | Model | Status | Calls | Input | Output | Reasoning | Cache read | Cache write | Estimated USD | Actual USD |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| base | acting | openai-codex | gpt-5.6-sol | failed_output | 35 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| base | acting | openai-codex | gpt-5.6-sol | succeeded | 265 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| base_self_review | acting | openai-codex | gpt-5.6-sol | failed_output | 29 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| base_self_review | acting | openai-codex | gpt-5.6-sol | succeeded | 271 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| moa_neutral | aggregator | openai-codex | gpt-5.6-sol | invalid_trace | 5 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| moa_neutral | aggregator | openai-codex | gpt-5.6-sol | succeeded | 295 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| moa_neutral | reference | openrouter | xiaomi/mimo-v2.5 | invalid_trace | 5 | 7500 | 81021 | 65538 | 5 | 0 | 0.0237358940 | unknown |
| moa_neutral | reference | openrouter | xiaomi/mimo-v2.5 | succeeded | 295 | 139226 | 4487779 | 4168227 | 462376 | 0 | 1.2773644128 | unknown |

## Trace audit

- Valid traces: 295
- Invalid traces: 5
- Reference calls: 295
- Reference input tokens: 139226
- Reference output tokens: 4487779
