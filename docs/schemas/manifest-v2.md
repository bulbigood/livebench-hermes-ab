# Manifest schema version 2

`manifest_schema_version` must equal `2`. A manifest freezes experiment identity, mandatory `arm_order`, baseline, every planned cell, provider-call count, execution and retry policy, scoring contract, upstream provenance, and Hermes compatibility result. The strict parser rejects missing, extra, or historical fields.
