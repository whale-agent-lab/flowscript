# Contributing

Thank you for helping improve FlowScript Skill Runtime. Contributions to the runtime, skill contracts, examples, documentation, and validation tooling are welcome.

## Before you start

- Search existing issues and pull requests before opening a duplicate.
- For a substantial DSL or architecture change, open an issue first and describe the use case, proposed contract, compatibility impact, and alternatives.
- Do not include secrets, private prompts, personal data, or unredacted production traces.
- Generated `runs/` directories are ignored and should not be committed. Add only deliberately sanitized fixtures when they are needed for a test.

## Development setup

From the repository root:

```bash
python -m venv .venv
```

Activate the environment, then install the runtime:

```bash
python -m pip install -e minimal_flowscript_agent
```

The project requires Python 3.11 or newer.

## Making changes

### Runtime changes

Keep workflow decisions in `WorkflowEngine`; models must not select commands, output paths, or branch targets. Preserve path confinement, argv-based execution, structured-state branching, timeouts, and inspectable artifacts.

### Skill changes

A runtime-compatible skill should keep `SKILL.md` readable to an ordinary agent and define controlled execution in exactly one `flow` block in `FLOWSCRIPT.md`.

When changing a skill:

- keep schemas, prompts, scripts, and DSL references consistent;
- preserve stable machine identifiers and status values;
- update replay fixtures when the input or artifact contract changes;
- validate both Chinese and English packages when the shared contract changes;
- do not commit generated runtime output.

### Documentation changes

Keep `README.md` and `README_cn.md` aligned in meaning. Examples must match the current CLI and artifact structure.

## Local checks

Compile the runtime:

```bash
python -m compileall -q minimal_flowscript_agent/minimize_agent
```

Validate both demo plans:

```bash
python -c "from pathlib import Path; from minimize_agent.flow_loader import load_flow, validate_plan; roots=[Path('skills_cn/csv-quality-report-demo').resolve(), Path('skills_en/csv-quality-report-demo').resolve()]; [validate_plan(load_flow(root), root) for root in roots]; print('Flow plans are valid')"
```

Run the same static checks used by GitHub Actions before submitting a pull request. A full end-to-end demo additionally requires an OpenAI-compatible local model endpoint.

## Pull requests

A pull request should:

- explain the problem and the chosen approach;
- identify behavior or contract changes;
- list checks that were run;
- update documentation and fixtures when relevant;
- avoid unrelated formatting or generated artifacts;
- remain small enough to review when practical.

## Reporting security issues

Do not disclose suspected vulnerabilities in a public issue. Follow [SECURITY.md](SECURITY.md).

## License of contributions

Unless you explicitly state otherwise, contributions intentionally submitted for inclusion in this project are licensed under the [Apache License 2.0](LICENSE), consistent with Section 5 of that license.