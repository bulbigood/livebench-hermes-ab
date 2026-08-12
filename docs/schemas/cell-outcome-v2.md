# Cell outcome schema version 2

`cell_journal_schema_version` must equal `2`. Every record contains one cell identity and exactly one terminal status: `valid` with an answer record and elapsed time, or `excluded` with an `ExclusionCode`, reason, and optional elapsed time. Attempts are retained separately; terminal promotion never deletes the previous authoritative record first.
