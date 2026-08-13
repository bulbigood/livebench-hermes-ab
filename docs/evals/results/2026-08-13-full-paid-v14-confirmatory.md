# LiveBench Hermes experiment

Common paired coverage: 295/300

| Arm | Mean |
|---|---:|
| base | 0.7740 |
| moa_mimo | 0.7635 |

## Exclusions

- INVALID_MOA_TRACE: 5

## Sampling

| Configured samples/task | Minimum common-valid samples/task | Recommended samples/task |
|---:|---:|---:|
| 20 | 18 | 20 |

## Paired better/worse decision analysis

The verdict uses a two-sided 95% confidence interval for common-valid paired score differences. Sample projections assume the observed effect and paired-difference variance persist; they are planning estimates, not guarantees.

| Candidate vs baseline | n | Mean delta | 95% CI | Verdict | Projected CI-excluding-zero samples/scenario | 95% power samples/scenario |
|---|---:|---:|---:|---|---:|---:|
| moa_mimo vs base | 295 | -0.0105 | [-0.0503, 0.0292] | inconclusive | 280 | 947 |

## Score by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 20 | 0.8444 | 0.8871 | 0.9371 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_mimo | 20 | 0.7766 | 0.8065 | 0.8734 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 20 | 0.1660 | 0.0213 | 1.0000 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_mimo | 20 | 0.7160 | 0.6915 | 0.9585 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | base | 19 | 0.8115 | 0.8548 | 0.9032 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_mimo | 19 | 0.5473 | 0.5000 | 0.8242 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base | 20 | 0.8979 | 0.9167 | 0.9167 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_mimo | 20 | 0.8521 | 0.8750 | 0.9208 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base | 20 | 1.0000 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_mimo | 20 | 0.8235 | 1.0000 | 1.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base | 19 | 0.9101 | 0.9167 | 0.9167 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_mimo | 19 | 0.8026 | 0.8333 | 0.9250 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base | 20 | 0.9300 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_mimo | 20 | 0.8755 | 1.0000 | 1.0000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base | 19 | 0.2744 | 0.0213 | 1.0000 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_mimo | 19 | 0.7458 | 0.7872 | 0.9191 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base | 20 | 1.0000 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_mimo | 20 | 1.0000 | 1.0000 | 1.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base | 20 | 0.8115 | 0.8300 | 0.9100 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_mimo | 20 | 0.8905 | 0.9100 | 0.9145 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base | 20 | 0.9500 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_mimo | 20 | 1.0000 | 1.0000 | 1.0000 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base | 20 | 0.3000 | 0.0000 | 1.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_mimo | 20 | 0.0000 | 0.0000 | 0.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base | 20 | 0.8000 | 0.8000 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_mimo | 20 | 0.4980 | 0.3300 | 0.8000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base | 20 | 1.0000 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_mimo | 20 | 1.0000 | 1.0000 | 1.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base | 18 | 0.9125 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_mimo | 18 | 0.9319 | 0.9500 | 1.0000 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Paired score deltas by scenario

Positive values favor the candidate over `base`.

| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | moa_mimo−base | 20 | -0.0677 | -0.0806 | 0.0573 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_mimo−base | 20 | 0.5500 | 0.5745 | 0.9372 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_mimo−base | 19 | -0.2643 | -0.2903 | 0.0565 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_mimo−base | 20 | -0.0458 | -0.0417 | 0.0437 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | moa_mimo−base | 20 | -0.1765 | 0.0000 | 0.0000 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | moa_mimo−base | 19 | -0.1075 | -0.0833 | 0.0083 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | moa_mimo−base | 20 | -0.0545 | 0.0000 | 0.5000 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | moa_mimo−base | 19 | 0.4714 | 0.5532 | 0.8787 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | moa_mimo−base | 20 | 0.0000 | 0.0000 | 0.0000 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | moa_mimo−base | 20 | 0.0790 | 0.0800 | 0.2115 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | moa_mimo−base | 20 | 0.0500 | 0.0000 | 0.0500 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | moa_mimo−base | 20 | -0.3000 | 0.0000 | 0.0000 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | moa_mimo−base | 20 | -0.3020 | -0.4700 | 0.0000 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_mimo−base | 20 | 0.0000 | 0.0000 | 0.0000 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | moa_mimo−base | 18 | 0.0194 | 0.0000 | 0.1850 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Score by family

| Family | Scenarios | Arm | n | Mean | Median | p95 |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base | 20 | 0.3000 | 0.0000 | 1.0000 |
| cta | 1 | moa_mimo | 20 | 0.0000 | 0.0000 | 0.0000 |
| math_comp | 1 | base | 20 | 0.9500 | 1.0000 | 1.0000 |
| math_comp | 1 | moa_mimo | 20 | 1.0000 | 1.0000 | 1.0000 |
| olympiad | 7 | base | 135 | 0.6853 | 0.8750 | 1.0000 |
| olympiad | 7 | moa_mimo | 135 | 0.7666 | 0.8298 | 0.9750 |
| paraphrase | 1 | base | 20 | 1.0000 | 1.0000 | 1.0000 |
| paraphrase | 1 | moa_mimo | 20 | 1.0000 | 1.0000 | 1.0000 |
| tablejoin | 5 | base | 100 | 0.9083 | 1.0000 | 1.0000 |
| tablejoin | 5 | moa_mimo | 100 | 0.8175 | 0.9100 | 1.0000 |

## Paired score deltas by family

Positive values favor the candidate over `base`.

| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | moa_mimo−base | 20 | -0.3000 | 0.0000 | 0.0000 |
| math_comp | 1 | moa_mimo−base | 20 | 0.0500 | 0.0000 | 0.0500 |
| olympiad | 7 | moa_mimo−base | 135 | 0.0813 | -0.0417 | 0.8723 |
| paraphrase | 1 | moa_mimo−base | 20 | 0.0000 | 0.0000 | 0.0000 |
| tablejoin | 5 | moa_mimo−base | 100 | -0.0908 | 0.0000 | 0.1720 |

## Overall wall time

Common-valid paired cells; values are seconds.

| Arm | n | Mean | Median | p95 |
|---|---:|---:|---:|---:|
| base | 295 | 64.0687 | 36.4480 | 260.8427 |
| moa_mimo | 295 | 214.7459 | 164.9073 | 487.3424 |

### Paired overall wall-time deltas

Positive values mean the candidate is slower than `base`.

| Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---:|---:|---:|
| moa_mimo−base | 295 | 150.6772 | 104.2559 | 389.0283 |

## Wall time by scenario

| Category | Family | Arm | n | Mean | Median | p95 | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | base | 20 | 86.4640 | 75.9317 | 135.2606 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_mimo | 20 | 356.8640 | 359.0326 | 526.8055 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | base | 20 | 225.4639 | 232.0785 | 281.1978 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_mimo | 20 | 407.2854 | 382.2344 | 631.6674 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | base | 19 | 120.0885 | 89.9152 | 218.1646 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_mimo | 19 | 344.0187 | 357.1652 | 430.5314 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | base | 20 | 46.3108 | 43.2718 | 65.9935 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| math | olympiad | moa_mimo | 20 | 308.6457 | 274.9202 | 511.4509 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | base | 20 | 11.8852 | 11.6839 | 15.5810 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| data_analysis | tablejoin | moa_mimo | 20 | 79.9641 | 83.4465 | 108.7667 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | base | 19 | 44.5551 | 42.2829 | 54.4880 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| math | olympiad | moa_mimo | 19 | 394.4005 | 376.7391 | 656.1762 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | base | 20 | 22.2723 | 19.4095 | 47.1166 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| data_analysis | tablejoin | moa_mimo | 20 | 126.1170 | 125.0771 | 160.5353 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | base | 19 | 229.8725 | 245.6529 | 280.5664 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| math | olympiad | moa_mimo | 19 | 392.1211 | 386.2420 | 492.6482 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | base | 20 | 17.2263 | 15.7008 | 20.9257 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| instruction_following | paraphrase | moa_mimo | 20 | 34.1228 | 32.9206 | 47.0726 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | base | 20 | 21.3258 | 20.8572 | 33.6223 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| data_analysis | tablejoin | moa_mimo | 20 | 67.1903 | 63.3355 | 93.4797 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | base | 20 | 31.2536 | 26.6071 | 51.9377 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| math | math_comp | moa_mimo | 20 | 171.4017 | 172.2824 | 210.4720 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | base | 20 | 11.2980 | 10.8030 | 18.5856 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | cta | moa_mimo | 20 | 68.2054 | 64.6686 | 108.5025 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | base | 20 | 33.9637 | 30.9068 | 59.6063 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_mimo | 20 | 86.0065 | 77.5812 | 128.1007 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | base | 20 | 6.8217 | 6.1369 | 11.6413 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| data_analysis | tablejoin | moa_mimo | 20 | 44.6448 | 41.6413 | 62.8476 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | base | 18 | 62.1528 | 59.3714 | 92.7156 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |
| math | olympiad | moa_mimo | 18 | 381.1563 | 340.1264 | 716.7953 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Paired wall-time deltas by scenario

Positive values mean the candidate is slower than `base`.

| Category | Family | Comparison | n | Mean Δ | Median Δ | p95 Δ | Scenario ID |
|---|---|---|---:|---:|---:|---:|---|
| math | olympiad | moa_mimo−base | 20 | 270.4000 | 259.5910 | 416.8809 | 0499deda2f068008d488551abf96b4b758c6ed6b79cd2ec6a204d1250b140421 |
| math | olympiad | moa_mimo−base | 20 | 181.8214 | 160.7533 | 416.5491 | 11f95734f602e7d1481f9887ca7fc8bed83258e22fd5c443449ac159a4732115 |
| math | olympiad | moa_mimo−base | 19 | 223.9302 | 198.3584 | 346.3878 | 2a82215ea19fcbded36fa95df35b6e7c5f6ed28b0b5f6c3460b4223f1904a536 |
| math | olympiad | moa_mimo−base | 20 | 262.3349 | 237.7382 | 467.0544 | 2dd75e080f3e276f3dcf304d970e6a03973ddf777537422c9aba59559ddc9594 |
| data_analysis | tablejoin | moa_mimo−base | 20 | 68.0789 | 72.7088 | 98.7857 | 4d351c29bdddf5c41d59cd7bd1b70bb4d2ae2a071ada382d7690066b1cd7764c |
| math | olympiad | moa_mimo−base | 19 | 349.8454 | 338.0337 | 603.9486 | 527d5f9f9cf27824b84109a495eeced7c7c097fb324b872212f6813a660e5ee4 |
| data_analysis | tablejoin | moa_mimo−base | 20 | 103.8446 | 98.0415 | 143.5797 | 539fd06729e1f852302dd51aab15ffa115225362425ef04808cdef88d000d300 |
| math | olympiad | moa_mimo−base | 19 | 162.2486 | 143.8562 | 324.6453 | 6dfb6aade6429e2cca0718a497a442299a57199dfd547813471f4cf30ed6c7c7 |
| instruction_following | paraphrase | moa_mimo−base | 20 | 16.8965 | 15.6727 | 29.7825 | 8c22986a688217ccbcb012c0e5b95acf6b0f6464501e0df4a0cf50c3526767d5 |
| data_analysis | tablejoin | moa_mimo−base | 20 | 45.8645 | 44.6897 | 77.3929 | a783dc9652728632d05f85ac5f944f71ffdfb2cc9dc6ea27e21ad80a96f44e48 |
| math | math_comp | moa_mimo−base | 20 | 140.1481 | 142.4106 | 179.8696 | a84e6c888591b8182c32e6ed18291d6eaf9eee366fa818b014e9da41028f9576 |
| data_analysis | cta | moa_mimo−base | 20 | 56.9074 | 51.6430 | 91.7511 | d3d910189e70e5e5edd9a3f76420da1e8a5578b966ceef1c3936fb6b8e456551 |
| data_analysis | tablejoin | moa_mimo−base | 20 | 52.0428 | 49.9924 | 90.0308 | d4b2efd567053821eedf1ea3f759d4948f50264b94bd6ff37b18bc92e79d4fc1 |
| data_analysis | tablejoin | moa_mimo−base | 20 | 37.8231 | 36.1217 | 55.2373 | d89584191190995d5cb7307c938dbfb201e3af17ed7f666c2afae0fe2ad55985 |
| math | olympiad | moa_mimo−base | 18 | 319.0035 | 290.9795 | 604.2481 | e5b72d9cdb39c6e5f8798a557f119fff35d98fd165f55659e71bf6ac38b5f178 |

## Wall time by family

| Family | Scenarios | Arm | n | Mean | Median | p95 |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | base | 20 | 11.2980 | 10.8030 | 18.5856 |
| cta | 1 | moa_mimo | 20 | 68.2054 | 64.6686 | 108.5025 |
| math_comp | 1 | base | 20 | 31.2536 | 26.6071 | 51.9377 |
| math_comp | 1 | moa_mimo | 20 | 171.4017 | 172.2824 | 210.4720 |
| olympiad | 7 | base | 135 | 116.8839 | 76.9949 | 279.4579 |
| olympiad | 7 | moa_mimo | 135 | 368.8665 | 356.8067 | 594.9180 |
| paraphrase | 1 | base | 20 | 17.2263 | 15.7008 | 20.9257 |
| paraphrase | 1 | moa_mimo | 20 | 34.1228 | 32.9206 | 47.0726 |
| tablejoin | 5 | base | 100 | 19.2537 | 14.8985 | 48.3913 |
| tablejoin | 5 | moa_mimo | 100 | 80.7846 | 72.3533 | 155.6737 |

## Paired wall-time deltas by family

Positive values mean the candidate is slower than `base`.

| Family | Scenarios | Comparison | n | Mean Δ | Median Δ | p95 Δ |
|---|---:|---|---:|---:|---:|---:|
| cta | 1 | moa_mimo−base | 20 | 56.9074 | 51.6430 | 91.7511 |
| math_comp | 1 | moa_mimo−base | 20 | 140.1481 | 142.4106 | 179.8696 |
| olympiad | 7 | moa_mimo−base | 135 | 251.9826 | 241.0976 | 502.5258 |
| paraphrase | 1 | moa_mimo−base | 20 | 16.8965 | 15.6727 | 29.7825 |
| tablejoin | 5 | moa_mimo−base | 100 | 61.5308 | 55.6265 | 135.3380 |

## Trace audit

- Valid traces: 295
- Invalid traces: 5
- Reference calls: 295
- Reference input tokens: 67535
- Reference output tokens: 4630140
