# LiveBench Hermes experiment

Common paired coverage: 295/300

| Arm | Mean | Delta vs baseline |
|---|---:|---:|
| base | 0.7740 | — |
| moa_mimo | 0.7635 | -0.0105 |

## Exclusions

- INVALID_MOA_TRACE: 5

## Statistical analysis

Configured samples per task: 20
Minimum common-valid samples per task: 18
Confidence level: 95%
Target margin of error: ±0.0500

| Arm | n | Tasks | Sample variance | Std. dev. | Std. error | 95% CI | Within-task variance | Recommended samples/task |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| base | 295 | 15 | 0.121955 | 0.349221 | 0.020332 | [0.7342, 0.8139] | 0.049576 | 20 |
| moa_mimo | 295 | 15 | 0.083875 | 0.289611 | 0.016862 | [0.7305, 0.7966] | 0.021248 | 20 |

Overall recommended samples/task: 20

Recommended sample counts are pilot estimates for the configured margin of error. Zero or unavailable observed within-task variance uses a conservative [0,1] score-range bound.

## Paired better/worse decision analysis

The verdict uses a two-sided 95% confidence interval for common-valid paired score differences. Sample projections assume the observed effect and paired-difference variance persist; they are planning estimates, not guarantees.

| Candidate vs baseline | n | Mean delta | SD | 95% CI | Verdict | Projected CI-excluding-zero samples/scenario | 95% power samples/scenario |
|---|---:|---:|---:|---:|---|---:|---:|
| moa_mimo vs base | 295 | -0.0105 | 0.348124 | [-0.0503, 0.0292] | inconclusive | 280 | 947 |

## Per-scenario statistics and percentiles

| Scenario | Category | Family | Arm/paired delta | n | Mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 | math | olympiad | base | 20 | 0.8444 | 0.1981 | 0.7976 | 0.8629 | 0.8871 | 0.9032 | 0.9371 |
| 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 | math | olympiad | moa_mimo | 20 | 0.7766 | 0.1177 | 0.4823 | 0.7661 | 0.8065 | 0.8387 | 0.8734 |
| 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 | math | olympiad | Δ moa_mimo−base | 20 | -0.0677 | 0.2449 | -0.3887 | -0.1371 | -0.0806 | -0.0282 | 0.0573 |
| 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 | math | olympiad | base | 20 | 0.1660 | 0.3534 | 0.0213 | 0.0213 | 0.0213 | 0.0213 | 1.0000 |
| 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 | math | olympiad | moa_mimo | 20 | 0.7160 | 0.1827 | 0.5096 | 0.5479 | 0.6915 | 0.8936 | 0.9585 |
| 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 | math | olympiad | Δ moa_mimo−base | 20 | 0.5500 | 0.3816 | -0.1245 | 0.4894 | 0.5745 | 0.8404 | 0.9372 |
| 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 | math | olympiad | base | 19 | 0.8115 | 0.1950 | 0.7274 | 0.8387 | 0.8548 | 0.8710 | 0.9032 |
| 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 | math | olympiad | moa_mimo | 19 | 0.5473 | 0.2265 | 0.2694 | 0.3280 | 0.5000 | 0.7984 | 0.8242 |
| 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 | math | olympiad | Δ moa_mimo−base | 19 | -0.2643 | 0.2708 | -0.6339 | -0.4785 | -0.2903 | -0.0403 | 0.0565 |
| 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 | math | olympiad | base | 20 | 0.8979 | 0.0286 | 0.8333 | 0.8750 | 0.9167 | 0.9167 | 0.9167 |
| 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 | math | olympiad | moa_mimo | 20 | 0.8521 | 0.0816 | 0.7438 | 0.8229 | 0.8750 | 0.9167 | 0.9208 |
| 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 | math | olympiad | Δ moa_mimo−base | 20 | -0.0458 | 0.0854 | -0.1729 | -0.0833 | -0.0417 | 0.0000 | 0.0437 |
| 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c | data_analysis | tablejoin | base | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c | data_analysis | tablejoin | moa_mimo | 20 | 0.8235 | 0.2477 | 0.4000 | 0.6525 | 1.0000 | 1.0000 | 1.0000 |
| 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c | data_analysis | tablejoin | Δ moa_mimo−base | 20 | -0.1765 | 0.2477 | -0.6000 | -0.3475 | 0.0000 | 0.0000 | 0.0000 |
| 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 | math | olympiad | base | 19 | 0.9101 | 0.0156 | 0.8750 | 0.9167 | 0.9167 | 0.9167 | 0.9167 |
| 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 | math | olympiad | moa_mimo | 19 | 0.8026 | 0.1136 | 0.5750 | 0.7708 | 0.8333 | 0.8333 | 0.9250 |
| 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 | math | olympiad | Δ moa_mimo−base | 19 | -0.1075 | 0.1165 | -0.3417 | -0.1458 | -0.0833 | -0.0417 | 0.0083 |
| 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 | data_analysis | tablejoin | base | 20 | 0.9300 | 0.1720 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 | data_analysis | tablejoin | moa_mimo | 20 | 0.8755 | 0.2323 | 0.3925 | 0.8900 | 1.0000 | 1.0000 | 1.0000 |
| 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | -0.0545 | 0.3118 | -0.6075 | -0.1100 | 0.0000 | 0.0000 | 0.5000 |
| 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 | math | olympiad | base | 19 | 0.2744 | 0.4355 | 0.0213 | 0.0213 | 0.0213 | 0.4681 | 1.0000 |
| 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 | math | olympiad | moa_mimo | 19 | 0.7458 | 0.1633 | 0.4830 | 0.5745 | 0.7872 | 0.8723 | 0.9191 |
| 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 | math | olympiad | Δ moa_mimo−base | 19 | 0.4714 | 0.4310 | -0.2340 | 0.1809 | 0.5532 | 0.8191 | 0.8787 |
| 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 | instruction_following | paraphrase | base | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 | instruction_following | paraphrase | moa_mimo | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 | instruction_following | paraphrase | Δ moa_mimo−base | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 | data_analysis | tablejoin | base | 20 | 0.8115 | 0.0685 | 0.6675 | 0.8300 | 0.8300 | 0.8300 | 0.9100 |
| a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 | data_analysis | tablejoin | moa_mimo | 20 | 0.8905 | 0.0493 | 0.8270 | 0.8750 | 0.9100 | 0.9100 | 0.9145 |
| a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | 0.0790 | 0.0803 | -0.0070 | 0.0750 | 0.0800 | 0.0850 | 0.2115 |
| a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 | math | math_comp | base | 20 | 0.9500 | 0.2236 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 | math | math_comp | moa_mimo | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 | math | math_comp | Δ moa_mimo−base | 20 | 0.0500 | 0.2236 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0500 |
| d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 | data_analysis | cta | base | 20 | 0.3000 | 0.4702 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 | data_analysis | cta | moa_mimo | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 | data_analysis | cta | Δ moa_mimo−base | 20 | -0.3000 | 0.4702 | -1.0000 | -1.0000 | 0.0000 | 0.0000 | 0.0000 |
| d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 | data_analysis | tablejoin | base | 20 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 | 0.8000 | 0.8000 |
| d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 | data_analysis | tablejoin | moa_mimo | 20 | 0.4980 | 0.2279 | 0.3300 | 0.3300 | 0.3300 | 0.8000 | 0.8000 |
| d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | -0.3020 | 0.2279 | -0.4700 | -0.4700 | -0.4700 | 0.0000 | 0.0000 |
| d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 | data_analysis | tablejoin | base | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 | data_analysis | tablejoin | moa_mimo | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 | math | olympiad | base | 18 | 0.9125 | 0.2227 | 0.8113 | 0.9500 | 0.9500 | 0.9875 | 1.0000 |
| e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 | math | olympiad | moa_mimo | 18 | 0.9319 | 0.0623 | 0.8175 | 0.9062 | 0.9500 | 0.9750 | 1.0000 |
| e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 | math | olympiad | Δ moa_mimo−base | 18 | 0.0194 | 0.2422 | -0.1750 | -0.0875 | 0.0000 | 0.0188 | 0.1850 |

## Per-family statistics and percentiles

| Family | Scenarios | Arm/paired delta | n | Mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cta | 1 | base | 20 | 0.3000 | 0.4702 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| cta | 1 | moa_mimo | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| cta | 1 | Δ moa_mimo−base | 20 | -0.3000 | 0.4702 | -1.0000 | -1.0000 | 0.0000 | 0.0000 | 0.0000 |
| math_comp | 1 | base | 20 | 0.9500 | 0.2236 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| math_comp | 1 | moa_mimo | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| math_comp | 1 | Δ moa_mimo−base | 20 | 0.0500 | 0.2236 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0500 |
| olympiad | 7 | base | 135 | 0.6853 | 0.3891 | 0.0213 | 0.4157 | 0.8750 | 0.9167 | 1.0000 |
| olympiad | 7 | moa_mimo | 135 | 0.7666 | 0.1805 | 0.4237 | 0.6872 | 0.8298 | 0.8843 | 0.9750 |
| olympiad | 7 | Δ moa_mimo−base | 135 | 0.0813 | 0.3960 | -0.4285 | -0.1064 | -0.0417 | 0.1788 | 0.8723 |
| paraphrase | 1 | base | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| paraphrase | 1 | moa_mimo | 20 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| paraphrase | 1 | Δ moa_mimo−base | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| tablejoin | 5 | base | 100 | 0.9083 | 0.1197 | 0.7270 | 0.8000 | 1.0000 | 1.0000 | 1.0000 |
| tablejoin | 5 | moa_mimo | 100 | 0.8175 | 0.2483 | 0.3300 | 0.8000 | 0.9100 | 1.0000 | 1.0000 |
| tablejoin | 5 | Δ moa_mimo−base | 100 | -0.0908 | 0.2447 | -0.6000 | -0.1550 | 0.0000 | 0.0000 | 0.1720 |

## Overall wall-time statistics

Timings use common-valid paired cells. Values are seconds; sums are cell-seconds, not pipeline elapsed time.

| Arm/paired delta | n | Mean | SD | Sum | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| base | 295 | 64.0687 | 75.2737 | 18900.2623 | 6.9691 | 14.7888 | 36.4480 | 71.5144 | 260.8427 |
| moa_mimo | 295 | 214.7459 | 164.9291 | 63350.0347 | 33.2222 | 67.0212 | 164.9073 | 351.1657 | 487.3424 |
| Δ moa_mimo−base | 295 | 150.6772 | 131.8616 | 44449.7724 | 16.3399 | 51.3398 | 104.2559 | 227.5462 | 389.0283 |

## Per-scenario wall-time statistics

| Scenario | Category | Family | Arm/paired delta | n | Mean | SD | Sum | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 | math | olympiad | base | 20 | 86.4640 | 35.7152 | 1729.2793 | 62.5973 | 69.4973 | 75.9317 | 83.8149 | 135.2606 |
| 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 | math | olympiad | moa_mimo | 20 | 356.8640 | 101.3349 | 7137.2795 | 225.7874 | 299.0326 | 359.0326 | 380.0556 | 526.8055 |
| 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 | math | olympiad | Δ moa_mimo−base | 20 | 270.4000 | 91.2165 | 5408.0001 | 151.5773 | 227.7865 | 259.5910 | 298.3857 | 416.8809 |
| 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 | math | olympiad | base | 20 | 225.4639 | 55.8337 | 4509.2786 | 137.4711 | 193.0618 | 232.0785 | 279.3630 | 281.1978 |
| 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 | math | olympiad | moa_mimo | 20 | 407.2854 | 122.4581 | 8145.7076 | 298.3747 | 350.6801 | 382.2344 | 417.0990 | 631.6674 |
| 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 | math | olympiad | Δ moa_mimo−base | 20 | 181.8214 | 141.8374 | 3636.4290 | 50.3008 | 90.1381 | 160.7533 | 194.3724 | 416.5491 |
| 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 | math | olympiad | base | 19 | 120.0885 | 55.1765 | 2281.6819 | 71.1259 | 81.4334 | 89.9152 | 157.6157 | 218.1646 |
| 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 | math | olympiad | moa_mimo | 19 | 344.0187 | 74.3327 | 6536.3560 | 257.5002 | 275.8956 | 357.1652 | 401.0132 | 430.5314 |
| 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 | math | olympiad | Δ moa_mimo−base | 19 | 223.9302 | 96.9453 | 4254.6741 | 72.1088 | 157.4088 | 198.3584 | 299.8335 | 346.3878 |
| 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 | math | olympiad | base | 20 | 46.3108 | 11.1972 | 926.2161 | 37.8427 | 39.1533 | 43.2718 | 46.3858 | 65.9935 |
| 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 | math | olympiad | moa_mimo | 20 | 308.6457 | 110.6846 | 6172.9139 | 199.6010 | 245.2106 | 274.9202 | 359.3970 | 511.4509 |
| 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 | math | olympiad | Δ moa_mimo−base | 20 | 262.3349 | 113.2479 | 5246.6979 | 138.3363 | 197.1075 | 237.7382 | 311.2338 | 467.0544 |
| 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c | data_analysis | tablejoin | base | 20 | 11.8852 | 3.8354 | 237.7039 | 8.3885 | 9.5428 | 11.6839 | 12.8594 | 15.5810 |
| 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c | data_analysis | tablejoin | moa_mimo | 20 | 79.9641 | 21.0367 | 1599.2829 | 47.9174 | 73.6982 | 83.4465 | 93.2154 | 108.7667 |
| 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c | data_analysis | tablejoin | Δ moa_mimo−base | 20 | 68.0789 | 21.9667 | 1361.5790 | 35.0914 | 62.2028 | 72.7088 | 81.9540 | 98.7857 |
| 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 | math | olympiad | base | 19 | 44.5551 | 7.6088 | 846.5468 | 35.4295 | 38.9537 | 42.2829 | 49.9307 | 54.4880 |
| 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 | math | olympiad | moa_mimo | 19 | 394.4005 | 135.4165 | 7493.6095 | 254.3920 | 290.5434 | 376.7391 | 438.2724 | 656.1762 |
| 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 | math | olympiad | Δ moa_mimo−base | 19 | 349.8454 | 134.6652 | 6647.0627 | 211.3023 | 239.4339 | 338.0337 | 396.8218 | 603.9486 |
| 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 | data_analysis | tablejoin | base | 20 | 22.2723 | 11.7289 | 445.4468 | 9.8715 | 15.9010 | 19.4095 | 23.8061 | 47.1166 |
| 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 | data_analysis | tablejoin | moa_mimo | 20 | 126.1170 | 28.3963 | 2522.3397 | 74.7553 | 108.3837 | 125.0771 | 152.2381 | 160.5353 |
| 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | 103.8446 | 29.2803 | 2076.8929 | 56.0530 | 89.7295 | 98.0415 | 135.3584 | 143.5797 |
| 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 | math | olympiad | base | 19 | 229.8725 | 50.8259 | 4367.5773 | 155.4338 | 210.0974 | 245.6529 | 268.4122 | 280.5664 |
| 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 | math | olympiad | moa_mimo | 19 | 392.1211 | 67.9575 | 7450.3015 | 310.5949 | 348.0942 | 386.2420 | 445.9323 | 492.6482 |
| 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 | math | olympiad | Δ moa_mimo−base | 19 | 162.2486 | 76.8767 | 3082.7242 | 78.8277 | 105.8779 | 143.8562 | 198.3921 | 324.6453 |
| 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 | instruction_following | paraphrase | base | 20 | 17.2263 | 5.2855 | 344.5260 | 13.9704 | 14.4497 | 15.7008 | 17.7482 | 20.9257 |
| 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 | instruction_following | paraphrase | moa_mimo | 20 | 34.1228 | 6.8820 | 682.4567 | 27.4107 | 28.9823 | 32.9206 | 38.4793 | 47.0726 |
| 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 | instruction_following | paraphrase | Δ moa_mimo−base | 20 | 16.8965 | 7.3998 | 337.9307 | 3.3245 | 13.3572 | 15.6727 | 19.9300 | 29.7825 |
| a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 | data_analysis | tablejoin | base | 20 | 21.3258 | 7.0669 | 426.5153 | 13.3753 | 15.3306 | 20.8572 | 26.6576 | 33.6223 |
| a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 | data_analysis | tablejoin | moa_mimo | 20 | 67.1903 | 21.4004 | 1343.8058 | 40.2071 | 54.6215 | 63.3355 | 73.3576 | 93.4797 |
| a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | 45.8645 | 22.6813 | 917.2905 | 10.8556 | 31.0388 | 44.6897 | 58.0236 | 77.3929 |
| a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 | math | math_comp | base | 20 | 31.2536 | 14.9555 | 625.0723 | 19.7665 | 23.2514 | 26.6071 | 31.1519 | 51.9377 |
| a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 | math | math_comp | moa_mimo | 20 | 171.4017 | 30.4386 | 3428.0335 | 133.3738 | 154.7028 | 172.2824 | 185.6029 | 210.4720 |
| a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 | math | math_comp | Δ moa_mimo−base | 20 | 140.1481 | 35.2535 | 2802.9612 | 91.9924 | 116.9735 | 142.4106 | 156.8528 | 179.8696 |
| d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 | data_analysis | cta | base | 20 | 11.2980 | 3.2251 | 225.9594 | 7.6099 | 9.5532 | 10.8030 | 11.9611 | 18.5856 |
| d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 | data_analysis | cta | moa_mimo | 20 | 68.2054 | 26.2408 | 1364.1078 | 41.5087 | 47.4958 | 64.6686 | 83.3630 | 108.5025 |
| d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 | data_analysis | cta | Δ moa_mimo−base | 20 | 56.9074 | 25.9433 | 1138.1484 | 30.5975 | 37.6961 | 51.6430 | 69.9358 | 91.7511 |
| d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 | data_analysis | tablejoin | base | 20 | 33.9637 | 15.6358 | 679.2745 | 13.2584 | 22.4632 | 30.9068 | 45.9345 | 59.6063 |
| d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 | data_analysis | tablejoin | moa_mimo | 20 | 86.0065 | 36.3287 | 1720.1304 | 48.4681 | 56.0880 | 77.5812 | 106.0860 | 128.1007 |
| d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | 52.0428 | 33.5659 | 1040.8559 | 15.5151 | 27.5285 | 49.9924 | 81.8056 | 90.0308 |
| d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 | data_analysis | tablejoin | base | 20 | 6.8217 | 2.5267 | 136.4343 | 4.3228 | 5.0261 | 6.1369 | 7.5497 | 11.6413 |
| d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 | data_analysis | tablejoin | moa_mimo | 20 | 44.6448 | 11.6032 | 892.8967 | 30.3725 | 37.9795 | 41.6413 | 53.5520 | 62.8476 |
| d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 | data_analysis | tablejoin | Δ moa_mimo−base | 20 | 37.8231 | 10.9291 | 756.4624 | 24.1145 | 31.2505 | 36.1217 | 43.1182 | 55.2373 |
| e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 | math | olympiad | base | 18 | 62.1528 | 19.9687 | 1118.7498 | 41.8777 | 47.6273 | 59.3714 | 65.8913 | 92.7156 |
| e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 | math | olympiad | moa_mimo | 18 | 381.1563 | 142.6318 | 6860.8133 | 261.3632 | 317.7633 | 340.1264 | 387.2421 | 716.7953 |
| e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 | math | olympiad | Δ moa_mimo−base | 18 | 319.0035 | 137.3333 | 5742.0635 | 177.0845 | 253.5966 | 290.9795 | 341.2518 | 604.2481 |

## Per-family wall-time statistics

| Family | Scenarios | Arm/paired delta | n | Mean | SD | Sum | p05 | p25 | p50 | p75 | p95 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cta | 1 | base | 20 | 11.2980 | 3.2251 | 225.9594 | 7.6099 | 9.5532 | 10.8030 | 11.9611 | 18.5856 |
| cta | 1 | moa_mimo | 20 | 68.2054 | 26.2408 | 1364.1078 | 41.5087 | 47.4958 | 64.6686 | 83.3630 | 108.5025 |
| cta | 1 | Δ moa_mimo−base | 20 | 56.9074 | 25.9433 | 1138.1484 | 30.5975 | 37.6961 | 51.6430 | 69.9358 | 91.7511 |
| math_comp | 1 | base | 20 | 31.2536 | 14.9555 | 625.0723 | 19.7665 | 23.2514 | 26.6071 | 31.1519 | 51.9377 |
| math_comp | 1 | moa_mimo | 20 | 171.4017 | 30.4386 | 3428.0335 | 133.3738 | 154.7028 | 172.2824 | 185.6029 | 210.4720 |
| math_comp | 1 | Δ moa_mimo−base | 20 | 140.1481 | 35.2535 | 2802.9612 | 91.9924 | 116.9735 | 142.4106 | 156.8528 | 179.8696 |
| olympiad | 7 | base | 135 | 116.8839 | 83.9755 | 15779.3298 | 38.2450 | 47.7086 | 76.9949 | 179.7747 | 279.4579 |
| olympiad | 7 | moa_mimo | 135 | 368.8665 | 113.0761 | 49796.9812 | 231.1294 | 291.9699 | 356.8067 | 407.7047 | 594.9180 |
| olympiad | 7 | Δ moa_mimo−base | 135 | 251.9826 | 129.4290 | 34017.6514 | 77.8579 | 165.9932 | 241.0976 | 313.6313 | 502.5258 |
| paraphrase | 1 | base | 20 | 17.2263 | 5.2855 | 344.5260 | 13.9704 | 14.4497 | 15.7008 | 17.7482 | 20.9257 |
| paraphrase | 1 | moa_mimo | 20 | 34.1228 | 6.8820 | 682.4567 | 27.4107 | 28.9823 | 32.9206 | 38.4793 | 47.0726 |
| paraphrase | 1 | Δ moa_mimo−base | 20 | 16.8965 | 7.3998 | 337.9307 | 3.3245 | 13.3572 | 15.6727 | 19.9300 | 29.7825 |
| tablejoin | 5 | base | 100 | 19.2537 | 13.2502 | 1925.3748 | 5.1193 | 9.8189 | 14.8985 | 23.9347 | 48.3913 |
| tablejoin | 5 | moa_mimo | 100 | 80.7846 | 36.4513 | 8078.4555 | 36.0871 | 52.5667 | 72.3533 | 102.7469 | 155.6737 |
| tablejoin | 5 | Δ moa_mimo−base | 100 | 61.5308 | 33.8632 | 6153.0807 | 16.9929 | 35.5593 | 55.6265 | 82.9664 | 135.3380 |

## Trace audit

- Valid traces: 295
- Invalid traces: 5
- Reference calls: 295
- Reference input tokens: 67535
- Reference output tokens: 4630140
