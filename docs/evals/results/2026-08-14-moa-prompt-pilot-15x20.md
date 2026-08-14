# LiveBench Hermes experiment

## Corrected executive conclusion

This report supersedes the earlier calculation from the same immutable four-arm run. The earlier scorer accepted 32 terminal `base` provider failures as model answers because Hermes exited with code `0`. The corrected scorer excludes them before forming the common-valid cohort.

Common paired coverage: 263/300

The corrected complete-case ordering is `base ≈ moa_neutral ≈ moa_critic > moa_legacy`. Critic and neutral no longer outperform `base`; the old uplift was driven by invalid failure strings in the baseline. Both wrapper arms remain better than legacy, while critic and neutral remain indistinguishable.

These are conditional diagnostic estimates, not a balanced confirmatory result. Failures are scenario-dependent: the minimum retained count is 2/20, and worst-case bounds for all missing pairs include zero. The CIs below describe only the 263 pairs where all four arms returned valid outputs.

| Arm | Mean | Median | Mean wall time |
|---|---:|---:|---:|
| `base` | 0.8627 | 0.9355 | 37.3 s |
| `moa_legacy` | 0.8091 | 0.9167 | 146.1 s |
| `moa_critic` | 0.8618 | 0.9167 | 140.7 s |
| `moa_neutral` | 0.8625 | 0.9167 | 141.4 s |

### Complete-case pairwise analysis

The first three comparisons are the frozen arm-versus-baseline questions. The final three are exploratory sidecar contrasts computed from the same corrected score rows.

| Contrast | Mean delta | 95% CI | Harm | Catastrophic harm | Worst-case missing-data bounds |
|---|---:|---:|---:|---:|---:|
| Legacy−base | −0.0536 | [−0.0803, −0.0269] | 29.7% | 4.9% | [−0.1703, +0.0763] |
| Critic−base | −0.0009 | [−0.0259, +0.0241] | 26.6% | 2.7% | [−0.1241, +0.1226] |
| Neutral−base | −0.0002 | [−0.0233, +0.0229] | 25.1% | 0.8% | [−0.1235, +0.1232] |
| Critic−legacy | +0.0527 | [+0.0228, +0.0827] | 20.2% | 2.7% | [−0.0771, +0.1696] |
| Critic−neutral | −0.0007 | [−0.0271, +0.0257] | 20.9% | 3.0% | [−0.1239, +0.1227] |
| Neutral−legacy | +0.0534 | [+0.0270, +0.0798] | 19.0% | 0.8% | [−0.0765, +0.1702] |

### What changed

| Metric | Earlier report | Corrected complete-case report |
|---|---:|---:|
| Common-valid pairs | 294/300 | 263/300 |
| `base` mean | 0.7740 | 0.8627 |
| `moa_legacy` mean | 0.8056 | 0.8091 |
| `moa_critic` mean | 0.8624 | 0.8618 |
| `moa_neutral` mean | 0.8603 | 0.8625 |
| Legacy−base | +0.0316 | −0.0536 |
| Critic−base | +0.0885 | −0.0009 |
| Neutral−base | +0.0863 | −0.0002 |
| Critic−legacy | +0.0569 | +0.0527 |
| Critic−neutral | +0.0021 | −0.0007 |

### Interpretation

- The untrusted wrapper repairs most of the degradation seen in legacy MoA, but does not improve quality over a successful plain call on this surviving cohort.
- The structured critic rubric has no demonstrated incremental value over neutral framing.
- `moa_neutral` is not a clean semantic placebo: the reference matched its requested constant template exactly in only 98/298 valid traces; most other outputs introduced task-dependent content.
- Family effects remain heterogeneous: versus base, critic is −0.0331 on olympiad, −0.0139 on tablejoin, +0.2500 on the single CTA scenario, −0.0526 on math competition, and +0.0300 on paraphrase.
- Neutral is slightly stronger on tablejoin (+0.0075) and weaker on olympiad (−0.0423); these shifts do not create an overall advantage.
- MoA mean latency is 3.8–3.9× the corrected base mean. There is no quality evidence here that justifies that default latency penalty.
- The operational reliability asymmetry remains important: base surfaced 32 failures while the MoA paths did not. That is a transport/retry finding, not evidence that MoA reasoning improved answers.

Corrected scoring generation: `7729f2e29ab841edaab31cc076d7302e`.

| Arm | Mean | Median |
|---|---:|---:|
| base | 0.8627 | 0.9355 |
| moa_legacy | 0.8091 | 0.9167 |
| moa_critic | 0.8618 | 0.9167 |
| moa_neutral | 0.8625 | 0.9167 |

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
- MODEL_OR_PROVIDER_FAILURE: 32

## Sampling

| Configured samples/task | Minimum common-valid samples/task | Recommended samples/task |
|---:|---:|---:|
| 20 | 2 | Unavailable |

> WARNING: fewer than 5 common-valid samples per task; variance-based planning estimates are unstable.

## Paired better/worse decision analysis

The verdict uses a two-sided 95% confidence interval for common-valid paired score differences. Sample projections assume the observed effect and paired-difference variance persist; they are planning estimates, not guarantees.
Catastrophic harm means a paired score delta `<= -0.5`.

| Candidate vs baseline | n | Mean delta | Median delta | Harm rate | Catastrophic harm rate | 95% CI | Verdict | Projected CI-excluding-zero samples/scenario | 95% power samples/scenario |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| moa_legacy vs base | 263 | -0.0536 | 0.0000 | 29.7% | 4.9% | [-0.0803, -0.0269] | worse | 5 | 15 |
| moa_critic vs base | 263 | -0.0009 | 0.0000 | 26.6% | 2.7% | [-0.0259, 0.0241] | inconclusive | 14526 | 49137 |
| moa_neutral vs base | 263 | -0.0002 | 0.0000 | 25.1% | 0.8% | [-0.0233, 0.0229] | inconclusive | 297078 | 1004942 |

## Missing-data sensitivity

The score and confidence-interval tables above are complete-case estimates conditional on every arm returning a valid output. Missingness is not assumed random. The bounds below assign every missing paired delta its worst possible value under the stated `[0, 1]` score range.

| Contrast | Observed pairs | Missing pairs | Worst-case mean-delta bounds |
|---|---:|---:|---:|
| moa_legacy_vs_base | 263 | 37 | [-0.1703, 0.0763] |
| moa_critic_vs_base | 263 | 37 | [-0.1241, 0.1226] |
| moa_neutral_vs_base | 263 | 37 | [-0.1235, 0.1232] |

## Score by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 19 | 0.9032 | 0.9032 | 0.9710 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_legacy | 19 | 0.7674 | 0.8710 | 0.9677 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_critic | 19 | 0.8565 | 0.8710 | 0.9710 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral | 19 | 0.8268 | 0.8548 | 0.9048 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 2 | 1.0000 | 1.0000 | 1.0000 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_legacy | 2 | 0.6489 | 0.6489 | 0.7160 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic | 2 | 0.9255 | 0.9255 | 0.9926 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral | 2 | 0.8404 | 0.8404 | 0.8500 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
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
| math | olympiad | base | 5 | 1.0000 | 1.0000 | 1.0000 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_legacy | 5 | 0.8553 | 0.9149 | 0.9830 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic | 5 | 0.8170 | 0.8298 | 0.9191 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral | 5 | 0.8766 | 0.8723 | 0.9234 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
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
| math | olympiad | moa_legacy−base | 2 | -0.3511 | -0.3511 | -0.2840 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic−base | 2 | -0.0745 | -0.0745 | -0.0074 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral−base | 2 | -0.1596 | -0.1596 | -0.1500 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
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
| math | olympiad | moa_legacy−base | 5 | -0.1447 | -0.0851 | -0.0170 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic−base | 5 | -0.1830 | -0.1702 | -0.0809 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral−base | 5 | -0.1234 | -0.1277 | -0.0766 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
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
| olympiad | 7 | base | 104 | 0.9122 | 0.9167 | 1.0000 |
| olympiad | 7 | moa_legacy | 104 | 0.8194 | 0.8750 | 1.0000 |
| olympiad | 7 | moa_critic | 104 | 0.8792 | 0.8750 | 1.0000 |
| olympiad | 7 | moa_neutral | 104 | 0.8699 | 0.8750 | 1.0000 |
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
| olympiad | 7 | moa_legacy−base | 104 | -0.0928 | -0.0323 | 0.0623 |
| olympiad | 7 | moa_critic−base | 104 | -0.0331 | -0.0250 | 0.0645 |
| olympiad | 7 | moa_neutral−base | 104 | -0.0423 | -0.0250 | 0.0645 |
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
| base | 263 | 37.2883 | 22.2209 | 88.4362 |
| moa_legacy | 263 | 146.1099 | 76.7752 | 411.0736 |
| moa_critic | 263 | 140.6849 | 84.7199 | 378.1423 |
| moa_neutral | 263 | 141.3812 | 56.2807 | 479.4243 |

### Paired overall wall-time deltas

Positive values mean the candidate is slower than `base`.

| Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---:|---:|---:|
| moa_legacy−base | 263 | 108.8216 | 53.8651 | 337.6681 |
| moa_critic−base | 263 | 103.3966 | 60.2733 | 314.8653 |
| moa_neutral−base | 263 | 104.0929 | 39.8877 | 434.6664 |

## Wall time by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 19 | 80.0686 | 77.2804 | 97.0695 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_legacy | 19 | 297.7336 | 289.7643 | 592.8112 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_critic | 19 | 297.8263 | 285.4803 | 627.0514 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_neutral | 19 | 271.6576 | 292.6967 | 442.1009 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 2 | 179.8292 | 179.8292 | 261.5986 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_legacy | 2 | 374.6296 | 374.6296 | 489.6538 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic | 2 | 256.6259 | 256.6259 | 262.0063 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral | 2 | 364.6689 | 364.6689 | 394.4202 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
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
| math | olympiad | base | 5 | 159.3567 | 170.9898 | 258.3077 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_legacy | 5 | 322.0681 | 317.1889 | 440.8859 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic | 5 | 299.8301 | 331.8757 | 384.6398 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral | 5 | 238.4536 | 277.0431 | 334.0956 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
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
| math | olympiad | moa_legacy−base | 2 | 194.8004 | 194.8004 | 228.0552 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_critic−base | 2 | 76.7967 | 76.7967 | 153.1856 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_neutral−base | 2 | 184.8398 | 184.8398 | 296.3604 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
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
| math | olympiad | moa_legacy−base | 5 | 162.7114 | 228.8634 | 287.8030 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_critic−base | 5 | 140.4734 | 226.2764 | 249.8940 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_neutral−base | 5 | 79.0968 | 106.0533 | 233.9679 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
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
| olympiad | 7 | base | 104 | 69.3584 | 59.4727 | 170.9673 |
| olympiad | 7 | moa_legacy | 104 | 273.2913 | 273.2790 | 550.4014 |
| olympiad | 7 | moa_critic | 104 | 259.5404 | 260.3828 | 496.0723 |
| olympiad | 7 | moa_neutral | 104 | 276.3838 | 278.1742 | 544.0194 |
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
| olympiad | 7 | moa_legacy−base | 104 | 203.9329 | 220.4158 | 467.1136 |
| olympiad | 7 | moa_critic−base | 104 | 190.1820 | 195.7149 | 456.6190 |
| olympiad | 7 | moa_neutral−base | 104 | 207.0255 | 208.5997 | 486.1310 |
| paraphrase | 1 | moa_legacy−base | 20 | 14.1824 | 13.4170 | 24.1805 |
| paraphrase | 1 | moa_critic−base | 20 | 19.5670 | 11.0671 | 41.0022 |
| paraphrase | 1 | moa_neutral−base | 20 | 14.4049 | 10.4442 | 44.6999 |
| tablejoin | 5 | moa_legacy−base | 100 | 40.9928 | 34.2374 | 111.1174 |
| tablejoin | 5 | moa_critic−base | 100 | 42.8830 | 42.3558 | 91.7295 |
| tablejoin | 5 | moa_neutral−base | 100 | 24.5006 | 19.4001 | 76.1783 |

## Mechanism proxies

candidate adoption is normalized substring matching; erroneous/useful adoption uses the objective candidate score and is not claim-level semantic annotation

| Arm | Trace cells | Reference outputs | Candidate present | Candidate scorable | Candidate score mean | Exact adoption | Useful adoption | Erroneous adoption | Structural violations | Underdetermination signals | Wrapper present |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| moa_critic | 298 | 298 | 153 | 153 | 0.5889 | 64 | 54 | 10 | 0 | 34 | 298 |
| moa_legacy | 298 | 298 | 0 | 0 | Unavailable | 0 | 0 | 0 | 0 | 2 | 0 |
| moa_neutral | 298 | 298 | 0 | 0 | Unavailable | 0 | 0 | 0 | 0 | 1 | 298 |

## Provider usage and billing completeness

- Evidence source: attempts
- Complete: False
- Recorded calls: 1788
- Cells/attempts without a provider ledger: 306
- Usage-complete calls: 894
- Cost-complete calls: 0
- Calls with provider generation IDs: 0

| Arm | Role | Provider | Model | Status | Calls | Input | Output | Reasoning | Cache read | Cache write | Estimated USD | Actual USD |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| moa_critic | aggregator | openai-codex | gpt-5.6-sol | succeeded | 298 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| moa_critic | reference | openrouter | xiaomi/mimo-v2.5 | succeeded | 298 | 350202 | 3792012 | 3402124 | 342504 | 0 | unknown | unknown |
| moa_legacy | aggregator | openai-codex | gpt-5.6-sol | succeeded | 298 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| moa_legacy | reference | openrouter | xiaomi/mimo-v2.5 | succeeded | 298 | 289346 | 3956983 | 3468669 | 393310 | 0 | unknown | unknown |
| moa_neutral | aggregator | openai-codex | gpt-5.6-sol | succeeded | 298 | 0 | 0 | 0 | 0 | 0 | unknown | unknown |
| moa_neutral | reference | openrouter | xiaomi/mimo-v2.5 | succeeded | 298 | 331734 | 3751224 | 3454404 | 259098 | 0 | unknown | unknown |

## Trace audit

- Valid traces: 894
- Invalid traces: 6
- Reference calls: 894
- Reference input tokens: 971282
- Reference output tokens: 11500219
