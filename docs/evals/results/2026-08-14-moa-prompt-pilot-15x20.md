# Hermes MoA critic/wrapper paid pilot — 15 scenarios × 20 samples

Common paired coverage: 294/300

| Arm | Mean | Median |
|---|---:|---:|
| base | 0.7740 | 0.9167 |
| moa_legacy | 0.8056 | 0.9100 |
| moa_critic | 0.8624 | 0.9167 |
| moa_neutral | 0.8603 | 0.9167 |

## Executive conclusion

The prompt-only intervention succeeded as a **combined wrapper/reference-framing change**, but this experiment does not identify the critic rubric as the cause.

- `moa_critic − base`: **+0.0885**, 95% CI **[+0.0510, +0.1259]**; harm rate **23.8%**; catastrophic-harm rate **2.4%**.
- `moa_neutral − base`: **+0.0863**, 95% CI **[+0.0505, +0.1221]**; harm rate **22.4%**; catastrophic-harm rate **0.7%**.
- `moa_legacy − base`: **+0.0316**, 95% CI **[-0.0061, +0.0693]**; inconclusive.
- Direct `critic − legacy`: **+0.0569**, 95% CI **[+0.0294, +0.0844]**.
- Direct `critic − neutral`: **+0.0021**, 95% CI **[-0.0223, +0.0266]**.

The improvement is stable from 10 to 20 samples: the critic delta moved from `+0.0816` to `+0.0885`, while its CI remained strictly above zero. The neutral arm remained essentially tied with critic. The strongest supported interpretation is therefore:

> Treating reference output as untrusted advisory data and preventing acting-agent role confusion materially improves this cohort. The additional structured critic rubric has no demonstrated incremental benefit over neutral non-acting framing.

This is a selection/mechanism cohort assembled from known failures, not an independent held-out confirmation. Do not present the result as general MoA superiority.

## Decision against the pre-registered success criteria

| Criterion | Result |
|---|---|
| Non-negative paired quality vs base | **Pass**: critic CI is entirely positive |
| Lower harm than legacy | **Pass descriptively**: 23.8% vs 26.5% |
| Lower catastrophic harm than legacy | **Pass descriptively**: 2.4% vs 4.4% |
| Structural/mechanism improvement | **Not established**: scenario scores improved, but claim-level adoption was not retained |
| References still contribute useful information | **Not established**: critic and neutral are statistically indistinguishable |
| Acceptable latency/cost | **Trade-off**: materially slower than base; reference spend remained modest |

The proper product decision is to retain the untrusted aggregator wrapper, keep `legacy` as a rollback/control mode, and treat the critic format as provisional until a held-out trace-retaining experiment separates it from neutral framing.

## Comparison with the frozen v14 result

The previous v14 confirmatory report used the same 15 scenarios and 20 samples but only compared base with legacy MiMo MoA. It found `moa_mimo − base = -0.0105`, 95% CI `[-0.0503, +0.0292]`, with tablejoin `−0.0908` and CTA `−0.3000` by family/scenario.

In this run:

- critic improved overall quality by `+0.0885` versus base;
- critic improved olympiad by `+0.1689` and CTA by `+0.2500`;
- critic tablejoin was approximately flat/slightly negative at `−0.0139` rather than v14's `−0.0908`;
- the within-run critic-versus-legacy comparison was positive, reducing reliance on cross-run comparisons.

CTA remains a floor sentinel: its positive movement is useful evidence against the specific legacy failure, not evidence that the underdetermined label problem has been solved generally.

## Reliability, tokens, cost, and trace limitation

- Planned pairs: **300**; common-valid pairs: **294** (**98.0%** coverage).
- Valid MoA traces: **894**; invalid traces: **6** (**0.67%** of 900 expected reference traces). Each MoA arm had two invalid traces.
- Reference tokens: **971,282 input** and **11,500,219 output**.
- At the observed OpenRouter list prices used for planning (`$0.14/M` input and `$0.28/M` output), estimated reference-model spend is approximately **$3.36**. Aggregator billing is separate and was not exposed by the harness, so this is not a total-cost claim.
- Mean wall time was **62.3 s** for base, **162.7 s** for legacy, **158.8 s** for critic, and **159.9 s** for neutral. The prompt change does not remove MoA's roughly 2.5× mean latency relative to base.
- The run preserves answers, objective scores, timing, usage summaries, and invalid-trace diagnostics. It does **not** preserve full valid reference blocks. Consequently, erroneous-claim copying, useful-claim adoption, candidate correctness, and underdetermination-detection rates cannot be reconstructed honestly from these artifacts.

That missing trace retention is the principal evidence gap. Before an independent confirmation, the harness should retain redacted valid reference and aggregator blocks as immutable artifacts.

### Paid usage ledger

The 15×20 row already includes the original samples 1–10; the 15×10 directory is therefore not added again. The smoke was a separate paid run. Counts below are persisted valid-reference usage records, not inferred call maxima.

| Stage | Arm | Recorded reference calls | Input tokens | Output tokens | Total tokens | Recorded cost field |
|---|---|---:|---:|---:|---:|---:|
| Smoke 15×1 | Legacy | 15 | 1,129 | 226,889 | 228,018 | $0.0637825104 |
| Smoke 15×1 | Critic | 15 | 34,835 | 246,730 | 281,565 | $0.0739642176 |
| Smoke 15×1 | Neutral | 15 | 30,184 | 244,420 | 274,604 | $0.0726648104 |
| Selection 15×20 | Legacy | 298 | 289,346 | 3,956,983 | 4,246,329 | $1.1495649480 |
| Selection 15×20 | Critic | 298 | 350,202 | 3,792,012 | 4,142,214 | $1.1117506512 |
| Selection 15×20 | Neutral | 298 | 331,734 | 3,751,224 | 4,082,958 | $1.0975109544 |
| **Paid total recorded** | **All reference arms** | **939** | **1,037,430** | **12,218,258** | **13,255,688** | **$3.5692380920** |

Every persisted `cost_usd` value has `cost_status: estimated` and `cost_source: provider_models_api`. Thus `$3.5692380920` is the exact sum of the recorded estimate fields, **not** an exact provider-billed total. Six invalid selection traces consumed calls but did not preserve usage, and OpenAI Codex aggregator usage/cost was not recorded. The current artifacts therefore cannot establish exact all-provider spend or total tokens. A future run should persist provider generation IDs, billed cost when available, aggregator usage, failed-call usage, and retry usage.

## Run provenance

Hermes source: `/home/dev/projects/hermes-moa-critic-0191`
Observed Hermes: `0.19.1`

<details>
<summary>Frozen run configuration</summary>

```yaml
# Four-arm prompt-only extension to 20 samples; samples 1-10 are imported from the frozen 10-sample run.
# A=base, B=legacy MoA, C=critic+untrusted wrapper, D=wrapper+neutral reference.
# Reference model, caps, fanout, and aggregator effort are identical across B/C/D.
experiment:
  id: livebench-hermes-moa-prompt-pilot-15x20-v1
  upstream_commit: 00eae856aa1c1a9e9d058a65a9a94d85884034c4
  release: '2026-06-25'
  seed: 5615
  question_globs:
  - data/live_bench/*/*/question.jsonl
selection:
  scenarios:
    instruction_following:
    - {id: 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5, family: paraphrase}
    math:
    - {id: a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576, family: math_comp}
    - {id: 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594, family: olympiad}
    - {id: 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115, family: olympiad}
    - {id: e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178, family: olympiad}
    - {id: 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4, family: olympiad}
    - {id: 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536, family: olympiad}
    - {id: 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7, family: olympiad}
    - {id: 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421, family: olympiad}
    data_analysis:
    - {id: d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985, family: tablejoin}
    - {id: a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48, family: tablejoin}
    - {id: 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300, family: tablejoin}
    - {id: d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551, family: cta}
    - {id: 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c, family: tablejoin}
    - {id: d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1, family: tablejoin}
generation:
  samples_per_task: 20
  retry: {max_attempts: 2, retryable_codes: []}
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
      model: {provider: openai-codex, default: gpt-5.6-sol}
      agent:
        reasoning_effort: low
        disabled_toolsets: &disabled [web, browser, terminal, file, code_execution, vision, video, image_gen, video_gen, bfl, x_search, tts, stt, skills, todo, memory, context_engine, session_search, clarify, delegation, cronjob, homeassistant, spotify, yuanbao, computer_use]
      moa: {enabled: false, save_traces: false}
  moa_legacy:
    credential_env: [OPENROUTER_API_KEY]
    hermes:
      model: {provider: moa, default: default}
      agent: {disabled_toolsets: *disabled}
      moa:
        enabled: true
        default_preset: default
        active_preset: default
        save_traces: true
        presets:
          default: &legacy_preset
            enabled: true
            advisory_prompt: legacy
            degraded_reference_policy: loud
            reference_max_tokens: 50000
            max_tokens: 4096
            fanout: every_n:3
            reference_models: &references
            - {provider: openrouter, model: xiaomi/mimo-v2.5}
            aggregator: &aggregator {provider: openai-codex, model: gpt-5.6-sol, reasoning_effort: low}
  moa_critic:
    credential_env: [OPENROUTER_API_KEY]
    hermes:
      model: {provider: moa, default: default}
      agent: {disabled_toolsets: *disabled}
      moa:
        enabled: true
        default_preset: default
        active_preset: default
        save_traces: true
        presets:
          default:
            enabled: true
            advisory_prompt: critic
            degraded_reference_policy: loud
            reference_max_tokens: 50000
            max_tokens: 4096
            fanout: every_n:3
            reference_models: *references
            aggregator: *aggregator
  moa_neutral:
    credential_env: [OPENROUTER_API_KEY]
    hermes:
      model: {provider: moa, default: default}
      agent: {disabled_toolsets: *disabled}
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
            reference_models: *references
            aggregator: *aggregator
scoring:
  implementation: livebench-objective-ground-truth
  schema_version: 2
```

</details>

## Exclusions

- INVALID_MOA_TRACE: 6

## Sampling

| Configured samples/task | Minimum common-valid samples/task | Recommended samples/task |
|---:|---:|---:|
| 20 | 19 | 20 |

## Paired better/worse decision analysis

The verdict uses a two-sided 95% confidence interval for common-valid paired score differences. Sample projections assume the observed effect and paired-difference variance persist; they are planning estimates, not guarantees.
Catastrophic harm means a paired score delta `<= -0.5`.

| Candidate vs baseline | n | Mean delta | Median delta | Harm rate | Catastrophic harm rate | 95% CI | Verdict | Projected CI-excluding-zero samples/scenario | 95% power samples/scenario |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| moa_legacy vs base | 294 | 0.0316 | 0.0000 | 26.5% | 4.4% | [-0.0061, 0.0693] | inconclusive | 28 | 95 |
| moa_critic vs base | 294 | 0.0885 | 0.0000 | 23.8% | 2.4% | [0.0510, 0.1259] | better | 4 | 12 |
| moa_neutral vs base | 294 | 0.0863 | 0.0000 | 22.4% | 0.7% | [0.0505, 0.1221] | better | 4 | 12 |

## Score by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 19 | 0.9032 | 0.9032 | 0.9710 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_legacy | 19 | 0.7674 | 0.8710 | 0.9677 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_critic | 19 | 0.8565 | 0.8710 | 0.9710 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral | 19 | 0.8268 | 0.8548 | 0.9048 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 19 | 0.1243 | 0.0213 | 1.0000 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_legacy | 19 | 0.7111 | 0.7234 | 0.9574 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic | 19 | 0.8555 | 0.8723 | 1.0000 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral | 19 | 0.8410 | 0.8723 | 0.9809 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | base | 20 | 0.8726 | 0.8710 | 0.9355 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_legacy | 20 | 0.6847 | 0.7661 | 0.9371 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_critic | 20 | 0.8290 | 0.8306 | 0.8895 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral | 20 | 0.8234 | 0.8306 | 0.9048 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base | 20 | 0.8979 | 0.9167 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_legacy | 20 | 0.8479 | 0.8542 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_critic | 20 | 0.8688 | 0.8750 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral | 20 | 0.8396 | 0.8750 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base | 20 | 1.0000 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_legacy | 20 | 0.8500 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_critic | 20 | 0.9400 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base | 19 | 0.8947 | 0.8750 | 0.9167 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_legacy | 19 | 0.8662 | 0.9167 | 0.9250 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_critic | 19 | 0.8969 | 0.9167 | 0.9250 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral | 19 | 0.9101 | 0.9167 | 1.0000 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base | 20 | 0.9110 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_legacy | 20 | 0.9945 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_critic | 20 | 0.9030 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral | 20 | 0.9195 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base | 19 | 0.2788 | 0.0213 | 1.0000 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_legacy | 19 | 0.8477 | 0.8936 | 1.0000 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic | 19 | 0.8723 | 0.9362 | 1.0000 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral | 19 | 0.8511 | 0.8723 | 0.9809 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base | 20 | 0.9700 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_legacy | 20 | 1.0000 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_critic | 20 | 1.0000 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base | 20 | 0.8270 | 0.8300 | 0.9100 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_legacy | 20 | 0.8590 | 0.8300 | 0.9145 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_critic | 20 | 0.8185 | 0.8300 | 0.9145 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral | 20 | 0.8725 | 0.8300 | 1.0000 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base | 19 | 1.0000 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_legacy | 19 | 1.0000 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_critic | 19 | 0.9474 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral | 19 | 1.0000 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base | 20 | 0.1500 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_legacy | 20 | 0.1000 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_critic | 20 | 0.4000 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral | 20 | 0.3000 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base | 20 | 0.8000 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_legacy | 20 | 0.6355 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_critic | 20 | 0.8000 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral | 20 | 0.7765 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base | 20 | 0.9930 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_legacy | 20 | 0.9900 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_critic | 20 | 1.0000 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base | 19 | 0.9632 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_legacy | 19 | 0.9447 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_critic | 19 | 0.9592 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral | 19 | 0.9553 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Paired score deltas by scenario

Positive values favor the candidate over `base`.

| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | moa_legacy−base | 19 | -0.1358 | -0.0645 | 0.0645 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_critic−base | 19 | -0.0467 | -0.0323 | 0.0677 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral−base | 19 | -0.0764 | -0.0645 | 0.0177 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_legacy−base | 19 | 0.5868 | 0.6170 | 0.9362 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic−base | 19 | 0.7312 | 0.8511 | 0.9404 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral−base | 19 | 0.7167 | 0.8511 | 0.9596 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_legacy−base | 20 | -0.1879 | -0.0806 | 0.0661 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_critic−base | 20 | -0.0435 | -0.0323 | 0.0492 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral−base | 20 | -0.0492 | -0.0565 | 0.0661 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_legacy−base | 20 | -0.0500 | -0.0417 | 0.0437 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_critic−base | 20 | -0.0292 | -0.0208 | 0.0833 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral−base | 20 | -0.0583 | -0.0417 | 0.0833 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | moa_legacy−base | 20 | -0.1500 | 0.0000 | 0.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_critic−base | 20 | -0.0600 | 0.0000 | 0.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral−base | 20 | 0.0000 | 0.0000 | 0.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | moa_legacy−base | 19 | -0.0285 | 0.0000 | 0.0500 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_critic−base | 19 | 0.0022 | 0.0000 | 0.0500 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral−base | 19 | 0.0154 | 0.0000 | 0.0833 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | moa_legacy−base | 20 | 0.0835 | 0.0000 | 0.5030 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_critic−base | 20 | -0.0080 | 0.0000 | 0.5030 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 0.0085 | 0.0000 | 0.5030 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | moa_legacy−base | 19 | 0.5689 | 0.8085 | 0.9787 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic−base | 19 | 0.5935 | 0.8511 | 0.9787 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral−base | 19 | 0.5722 | 0.8298 | 0.9596 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | moa_legacy−base | 20 | 0.0300 | 0.0000 | 0.0300 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_critic−base | 20 | 0.0300 | 0.0000 | 0.0300 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral−base | 20 | 0.0300 | 0.0000 | 0.0300 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | moa_legacy−base | 20 | 0.0320 | 0.0000 | 0.1400 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_critic−base | 20 | -0.0085 | 0.0000 | 0.0875 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 0.0455 | 0.0000 | 0.1730 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | moa_legacy−base | 19 | 0.0000 | 0.0000 | 0.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_critic−base | 19 | -0.0526 | 0.0000 | 0.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral−base | 19 | 0.0000 | 0.0000 | 0.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | moa_legacy−base | 20 | -0.0500 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_critic−base | 20 | 0.2500 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral−base | 20 | 0.1500 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | moa_legacy−base | 20 | -0.1645 | 0.0000 | 0.0000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_critic−base | 20 | 0.0000 | 0.0000 | 0.0000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral−base | 20 | -0.0235 | 0.0000 | 0.0000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_legacy−base | 20 | -0.0030 | 0.0000 | 0.0070 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_critic−base | 20 | 0.0070 | 0.0000 | 0.0070 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 0.0070 | 0.0000 | 0.0070 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | moa_legacy−base | 19 | -0.0184 | 0.0000 | 0.0500 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_critic−base | 19 | -0.0039 | 0.0000 | 0.0500 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral−base | 19 | -0.0079 | 0.0000 | 0.0500 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Score by family

| Family | Scenarios | Arm | n | Mean | Median | p95 |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base | 20 | 0.1500 | 0.0000 | 1.0000 |
| cta | 1 | moa_legacy | 20 | 0.1000 | 0.0000 | 1.0000 |
| cta | 1 | moa_critic | 20 | 0.4000 | 0.0000 | 1.0000 |
| cta | 1 | moa_neutral | 20 | 0.3000 | 0.0000 | 1.0000 |
| math_comp | 1 | base | 19 | 1.0000 | 1.0000 | 1.0000 |
| math_comp | 1 | moa_legacy | 19 | 1.0000 | 1.0000 | 1.0000 |
| math_comp | 1 | moa_critic | 19 | 0.9474 | 1.0000 | 1.0000 |
| math_comp | 1 | moa_neutral | 19 | 1.0000 | 1.0000 | 1.0000 |
| olympiad | 7 | base | 135 | 0.7076 | 0.9032 | 1.0000 |
| olympiad | 7 | moa_legacy | 135 | 0.8093 | 0.8710 | 1.0000 |
| olympiad | 7 | moa_critic | 135 | 0.8765 | 0.8750 | 1.0000 |
| olympiad | 7 | moa_neutral | 135 | 0.8634 | 0.8750 | 1.0000 |
| paraphrase | 1 | base | 20 | 0.9700 | 1.0000 | 1.0000 |
| paraphrase | 1 | moa_legacy | 20 | 1.0000 | 1.0000 | 1.0000 |
| paraphrase | 1 | moa_critic | 20 | 1.0000 | 1.0000 | 1.0000 |
| paraphrase | 1 | moa_neutral | 20 | 1.0000 | 1.0000 | 1.0000 |
| tablejoin | 5 | base | 100 | 0.9062 | 1.0000 | 1.0000 |
| tablejoin | 5 | moa_legacy | 100 | 0.8658 | 1.0000 | 1.0000 |
| tablejoin | 5 | moa_critic | 100 | 0.8923 | 1.0000 | 1.0000 |
| tablejoin | 5 | moa_neutral | 100 | 0.9137 | 1.0000 | 1.0000 |

## Paired score deltas by family

Positive values favor the candidate over `base`.

| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | moa_legacy−base | 20 | -0.0500 | 0.0000 | 1.0000 |
| cta | 1 | moa_critic−base | 20 | 0.2500 | 0.0000 | 1.0000 |
| cta | 1 | moa_neutral−base | 20 | 0.1500 | 0.0000 | 1.0000 |
| math_comp | 1 | moa_legacy−base | 19 | 0.0000 | 0.0000 | 0.0000 |
| math_comp | 1 | moa_critic−base | 19 | -0.0526 | 0.0000 | 0.0000 |
| math_comp | 1 | moa_neutral−base | 19 | 0.0000 | 0.0000 | 0.0000 |
| olympiad | 7 | moa_legacy−base | 135 | 0.1017 | 0.0000 | 0.9149 |
| olympiad | 7 | moa_critic−base | 135 | 0.1689 | 0.0000 | 0.9362 |
| olympiad | 7 | moa_neutral−base | 135 | 0.1558 | 0.0000 | 0.8936 |
| paraphrase | 1 | moa_legacy−base | 20 | 0.0300 | 0.0000 | 0.0300 |
| paraphrase | 1 | moa_critic−base | 20 | 0.0300 | 0.0000 | 0.0300 |
| paraphrase | 1 | moa_neutral−base | 20 | 0.0300 | 0.0000 | 0.0300 |
| tablejoin | 5 | moa_legacy−base | 100 | -0.0404 | 0.0000 | 0.1400 |
| tablejoin | 5 | moa_critic−base | 100 | -0.0139 | 0.0000 | 0.0815 |
| tablejoin | 5 | moa_neutral−base | 100 | 0.0075 | 0.0000 | 0.1415 |

## Overall wall time

Common-valid paired cells; values are seconds.

| Arm | n | Mean | Median | p95 |
|---|---:|---:|---:|---:|
| base | 294 | 62.3024 | 26.6589 | 279.7177 |
| moa_legacy | 294 | 162.7214 | 93.5921 | 435.9292 |
| moa_critic | 294 | 158.7606 | 93.9110 | 405.4153 |
| moa_neutral | 294 | 159.8823 | 68.2960 | 515.4462 |

### Paired overall wall-time deltas

Positive values mean the candidate is slower than `base`.

| Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---:|---:|---:|
| moa_legacy−base | 294 | 100.4190 | 51.6692 | 335.3044 |
| moa_critic−base | 294 | 96.4582 | 54.1555 | 313.0556 |
| moa_neutral−base | 294 | 97.5799 | 41.4657 | 423.1074 |

## Wall time by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 19 | 80.0686 | 77.2804 | 97.0695 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_legacy | 19 | 297.7336 | 289.7643 | 592.8112 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_critic | 19 | 297.8263 | 285.4803 | 627.0514 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral | 19 | 271.6576 | 292.6967 | 442.1009 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 19 | 266.1143 | 279.4215 | 281.4790 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_legacy | 19 | 301.5984 | 313.9196 | 402.8904 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic | 19 | 304.6954 | 306.8670 | 588.3785 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral | 19 | 359.2427 | 341.5880 | 653.2338 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | base | 20 | 95.8706 | 85.5549 | 171.3173 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_legacy | 20 | 262.1212 | 253.7305 | 553.5901 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_critic | 20 | 229.2892 | 264.1171 | 349.6143 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral | 20 | 280.7706 | 282.8191 | 625.9099 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base | 20 | 41.3351 | 40.2117 | 62.2037 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_legacy | 20 | 250.0479 | 251.0369 | 384.9799 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_critic | 20 | 271.5733 | 237.9028 | 539.2998 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral | 20 | 271.8383 | 246.4826 | 521.1849 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base | 20 | 11.1605 | 10.3241 | 18.8399 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_legacy | 20 | 59.4760 | 64.1101 | 126.1133 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_critic | 20 | 60.2790 | 62.8505 | 117.9000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral | 20 | 44.6304 | 32.9870 | 89.8961 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base | 19 | 41.9929 | 39.7765 | 49.6527 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_legacy | 19 | 251.4138 | 265.8574 | 466.4922 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_critic | 19 | 243.2337 | 238.8718 | 443.8081 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral | 19 | 295.6634 | 238.0308 | 566.2192 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base | 20 | 18.5384 | 19.1681 | 26.9928 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_legacy | 20 | 63.4390 | 63.2584 | 98.7746 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_critic | 20 | 63.7669 | 61.9681 | 121.3073 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral | 20 | 47.3916 | 33.6838 | 94.9725 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base | 19 | 242.6491 | 279.4538 | 280.8152 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_legacy | 19 | 318.0213 | 314.6512 | 557.5521 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic | 19 | 310.4562 | 316.1320 | 567.6904 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral | 19 | 258.8486 | 295.0594 | 437.2614 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base | 20 | 16.1366 | 16.2493 | 17.7710 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_legacy | 20 | 30.3191 | 28.2156 | 40.6905 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_critic | 20 | 35.7037 | 30.3522 | 55.7109 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral | 20 | 30.5415 | 27.2914 | 61.1131 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base | 20 | 14.3293 | 12.3699 | 23.0784 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_legacy | 20 | 50.1987 | 49.9845 | 78.8077 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_critic | 20 | 60.4629 | 57.8070 | 89.8276 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral | 20 | 41.5423 | 42.9726 | 69.7478 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base | 19 | 21.3016 | 20.7637 | 25.3308 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_legacy | 19 | 144.4934 | 134.8016 | 225.4886 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_critic | 19 | 136.0714 | 141.0680 | 193.5941 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral | 19 | 160.6004 | 177.2964 | 221.5690 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base | 20 | 10.0166 | 9.4244 | 15.5398 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_legacy | 20 | 44.3906 | 48.1048 | 76.7829 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_critic | 20 | 37.7218 | 38.4639 | 65.3914 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral | 20 | 33.0640 | 32.6772 | 63.7764 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base | 20 | 32.6719 | 26.6589 | 66.0036 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_legacy | 20 | 78.0663 | 58.2751 | 214.3242 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_critic | 20 | 70.6909 | 77.4416 | 103.0379 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral | 20 | 43.3353 | 28.8179 | 93.4748 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base | 20 | 6.5880 | 5.6849 | 9.6365 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_legacy | 20 | 37.0719 | 34.2387 | 66.1595 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_critic | 20 | 42.5034 | 44.8544 | 74.2438 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral | 20 | 28.8918 | 31.2339 | 43.9004 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base | 19 | 52.2920 | 50.3519 | 69.8317 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_legacy | 19 | 283.4481 | 282.8383 | 590.0224 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_critic | 19 | 246.4426 | 270.3664 | 361.9949 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral | 19 | 262.6863 | 295.7010 | 463.2587 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Paired wall-time deltas by scenario

Positive values mean the candidate is slower than `base`.

| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | moa_legacy−base | 19 | 217.6650 | 216.9188 | 513.0915 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_critic−base | 19 | 217.7577 | 205.1308 | 544.7153 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral−base | 19 | 191.5890 | 214.4157 | 371.3870 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_legacy−base | 19 | 35.4841 | 54.6803 | 165.2406 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic−base | 19 | 38.5811 | 31.4532 | 310.8484 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral−base | 19 | 93.1285 | 61.4582 | 379.2817 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_legacy−base | 20 | 166.2506 | 169.0503 | 469.2800 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_critic−base | 20 | 133.4186 | 144.7999 | 271.8578 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_neutral−base | 20 | 184.8999 | 195.2858 | 547.4164 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_legacy−base | 20 | 208.7128 | 215.0219 | 349.0426 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_critic−base | 20 | 230.2382 | 198.9484 | 478.3102 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_neutral−base | 20 | 230.5032 | 206.5445 | 482.0187 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | moa_legacy−base | 20 | 48.3155 | 52.9918 | 113.2125 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_critic−base | 20 | 49.1185 | 43.5371 | 107.4218 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_neutral−base | 20 | 33.4698 | 20.3969 | 79.8208 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | moa_legacy−base | 19 | 209.4210 | 228.2391 | 420.8103 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_critic−base | 19 | 201.2408 | 197.4522 | 398.2204 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_neutral−base | 19 | 253.6706 | 198.7459 | 527.7460 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | moa_legacy−base | 20 | 44.9007 | 47.0427 | 77.3692 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_critic−base | 20 | 45.2285 | 45.9387 | 94.3145 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 28.8532 | 16.5574 | 80.8461 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | moa_legacy−base | 19 | 75.3722 | 33.6838 | 297.1393 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic−base | 19 | 67.8071 | 35.9699 | 286.7433 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral−base | 19 | 16.1995 | 65.9696 | 180.2316 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | moa_legacy−base | 20 | 14.1824 | 13.4170 | 24.1805 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_critic−base | 20 | 19.5670 | 11.0671 | 41.0022 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_neutral−base | 20 | 14.4049 | 10.4442 | 44.6999 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | moa_legacy−base | 20 | 35.8694 | 33.3081 | 59.0221 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_critic−base | 20 | 46.1336 | 44.8609 | 77.2992 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 27.2129 | 21.8300 | 60.4692 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | moa_legacy−base | 19 | 123.1918 | 115.2279 | 202.6151 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_critic−base | 19 | 114.7698 | 122.4973 | 171.6105 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_neutral−base | 19 | 139.2988 | 157.4265 | 201.1472 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | moa_legacy−base | 20 | 34.3740 | 38.5263 | 68.2907 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_critic−base | 20 | 27.7052 | 29.6659 | 50.4777 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_neutral−base | 20 | 23.0474 | 18.8998 | 53.0479 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | moa_legacy−base | 20 | 45.3944 | 29.2771 | 200.7845 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_critic−base | 20 | 38.0189 | 36.1687 | 83.1245 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 10.6634 | 2.9852 | 67.8698 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_legacy−base | 20 | 30.4839 | 27.6298 | 61.9237 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_critic−base | 20 | 35.9154 | 40.1336 | 70.1226 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_neutral−base | 20 | 22.3038 | 26.1780 | 39.8342 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | moa_legacy−base | 19 | 231.1562 | 226.6988 | 539.5365 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_critic−base | 19 | 194.1506 | 218.8154 | 309.9060 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_neutral−base | 19 | 210.3943 | 234.5000 | 410.2412 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Wall time by family

| Family | Scenarios | Arm | n | Mean | Median | p95 |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base | 20 | 10.0166 | 9.4244 | 15.5398 |
| cta | 1 | moa_legacy | 20 | 44.3906 | 48.1048 | 76.7829 |
| cta | 1 | moa_critic | 20 | 37.7218 | 38.4639 | 65.3914 |
| cta | 1 | moa_neutral | 20 | 33.0640 | 32.6772 | 63.7764 |
| math_comp | 1 | base | 19 | 21.3016 | 20.7637 | 25.3308 |
| math_comp | 1 | moa_legacy | 19 | 144.4934 | 134.8016 | 225.4886 |
| math_comp | 1 | moa_critic | 19 | 136.0714 | 141.0680 | 193.5941 |
| math_comp | 1 | moa_neutral | 19 | 160.6004 | 177.2964 | 221.5690 |
| olympiad | 7 | base | 135 | 116.4691 | 72.8455 | 280.2514 |
| olympiad | 7 | moa_legacy | 135 | 280.2627 | 283.6443 | 551.2543 |
| olympiad | 7 | moa_critic | 135 | 271.6124 | 269.4682 | 557.3942 |
| olympiad | 7 | moa_neutral | 135 | 285.6744 | 290.5955 | 558.5429 |
| paraphrase | 1 | base | 20 | 16.1366 | 16.2493 | 17.7710 |
| paraphrase | 1 | moa_legacy | 20 | 30.3191 | 28.2156 | 40.6905 |
| paraphrase | 1 | moa_critic | 20 | 35.7037 | 30.3522 | 55.7109 |
| paraphrase | 1 | moa_neutral | 20 | 30.5415 | 27.2914 | 61.1131 |
| tablejoin | 5 | base | 100 | 16.6576 | 12.9898 | 34.4073 |
| tablejoin | 5 | moa_legacy | 100 | 57.6504 | 52.7173 | 125.9726 |
| tablejoin | 5 | moa_critic | 100 | 59.5406 | 55.2129 | 111.0234 |
| tablejoin | 5 | moa_neutral | 100 | 41.1583 | 31.7216 | 89.6442 |

## Paired wall-time deltas by family

Positive values mean the candidate is slower than `base`.

| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | moa_legacy−base | 20 | 34.3740 | 38.5263 | 68.2907 |
| cta | 1 | moa_critic−base | 20 | 27.7052 | 29.6659 | 50.4777 |
| cta | 1 | moa_neutral−base | 20 | 23.0474 | 18.8998 | 53.0479 |
| math_comp | 1 | moa_legacy−base | 19 | 123.1918 | 115.2279 | 202.6151 |
| math_comp | 1 | moa_critic−base | 19 | 114.7698 | 122.4973 | 171.6105 |
| math_comp | 1 | moa_neutral−base | 19 | 139.2988 | 157.4265 | 201.1472 |
| olympiad | 7 | moa_legacy−base | 135 | 163.7936 | 188.6086 | 438.0373 |
| olympiad | 7 | moa_critic−base | 135 | 155.1433 | 178.3665 | 403.2604 |
| olympiad | 7 | moa_neutral−base | 135 | 169.2053 | 187.4497 | 478.7912 |
| paraphrase | 1 | moa_legacy−base | 20 | 14.1824 | 13.4170 | 24.1805 |
| paraphrase | 1 | moa_critic−base | 20 | 19.5670 | 11.0671 | 41.0022 |
| paraphrase | 1 | moa_neutral−base | 20 | 14.4049 | 10.4442 | 44.6999 |
| tablejoin | 5 | moa_legacy−base | 100 | 40.9928 | 34.2374 | 111.1174 |
| tablejoin | 5 | moa_critic−base | 100 | 42.8830 | 42.3558 | 91.7295 |
| tablejoin | 5 | moa_neutral−base | 100 | 24.5006 | 19.4001 | 76.1783 |

## Trace audit

- Valid traces: 894
- Invalid traces: 6
- Reference calls: 894
- Reference input tokens: 971282
- Reference output tokens: 11500219
