# Flow Contract

The workflow runs request parsing, input validation, synthetic-data generation and profiling, LLM interpretation in English, interpretation validation, and report finalization in order.

The employee list, region list, and grouping dimension are required. The date range is optional; when omitted, the validation script writes an inclusive range covering the most recent 30 days through today. The LLM interpretation must produce a JSON object with a non-empty `summary` string and string arrays named `risks`, `recommendations`, and `cluster_insights`.

Every branch reads only the `state` field from a status file. Only `valid` or `success` may advance the workflow. `needs_input` enters clarification. `invalid` and `recoverable_error` switch to standard mode after the corresponding script writes fallback context. `fatal_error` writes status and terminates.
