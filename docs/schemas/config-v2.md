# Config schema version 2

The authoritative schema is parsed by `livebench_hermes_ab.config.parse_config`. All seven top-level sections are mandatory and unknown keys are rejected. Arms are an ordered mapping. Retry, execution mode, compatibility, and the scoring implementation/version each have exactly one representation. There is no legacy normalization.
