# Attempt envelope schema v1

Every `attempts/*-attempt-N.json` file is immutable and written atomically before promotion of its
terminal outcome. Required fields are `attempt_schema_version: 1` and `outcome`, whose value is a
cell-outcome-v2 object.

An excluded MoA attempt may also contain:

```json
{
  "diagnostic": {
    "kind": "moa_trace",
    "encoding": "utf-8",
    "content": "<raw trace JSONL>"
  }
}
```

Malformed non-UTF-8 traces use `encoding: "base64"` so the original bytes remain recoverable.

The diagnostic preserves provider and trace evidence that would otherwise disappear when the
isolated cell home is cleaned. It is attempt-local: it is not copied into `cells/`, execution
generations, scoring generations, or reports. Treat run directories as potentially sensitive
because provider diagnostics can contain prompts and model outputs.