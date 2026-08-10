# LiveBench Hermes BASE vs MoA — traced smoke

**Verdict:** `PROMISING_NOT_CONCLUSIVE`
**Technical validity:** `VALID_WITH_BASE_TOKEN_TELEMETRY_LIMITATION`

## Result

- Pairs: 5
- BASE mean: 0.4043
- MoA mean: 0.5995
- Mean paired delta: +0.1952
- Median paired delta: +0.0000
- Bootstrap 95% interval: [0.0000, 0.5356]
- Improved / tied / regressed: 2 / 3 / 0

## Latency

- BASE: 609.6s
- MoA: 739.2s
- Overhead: +129.6s (+21.3%)

## Integrity

- MoA traces: 5/5
- Valid Minimax references: 5/5
- Reference tokens: 8784 input, 33320 output
- Aggregator outputs match answer artifacts: True
- Tools: zero schemas in both arms
- Scoring: pinned objective LiveBench task processors

## Limitations

- Only five heterogeneous tasks; this is a demanding smoke test, not a stable population estimate.
- Two BASE sessions did not persist token usage; latency and scores are complete, BASE token totals are not.
- The bootstrap interval includes zero and is descriptive for the frozen five-task sample only.

The earlier untraced run is preserved but excluded from the headline because it could not prove reference cardinality.
