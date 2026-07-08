# Security Policy

## Project status

FlowScript Skill Runtime is an experimental validation-oriented MVP. It constrains workflow execution, but it is not a hardened sandbox and should not be used to execute untrusted skills or unreviewed Python scripts.

Until versioned releases are published, security fixes are made on the default branch only.

## Reporting a vulnerability

Please do not open a public issue for an undisclosed vulnerability.

Use GitHub Private Vulnerability Reporting or a private Security Advisory for this repository when available. If private reporting is not enabled, contact the repository owner privately through the contact method listed on their GitHub profile and share only enough public information to establish a secure channel.

Include, when possible:

- the affected commit or version;
- the relevant skill, DSL node, or runtime component;
- reproduction steps or a minimal proof of concept;
- expected and observed behavior;
- security impact and required preconditions;
- any suggested mitigation.

Do not include real credentials, personal data, or destructive payloads.

## Security boundaries

The runtime currently enforces several defensive constraints:

- executable nodes must declare Python scripts;
- subprocesses use argv and `shell=False`;
- script and artifact paths must remain under the skill root;
- working directories are fixed to the skill root;
- accepted exit codes and timeouts are declared;
- models cannot choose commands or branch targets;
- branch decisions use structured status artifacts.

These controls do not make bundled scripts safe. An allowed Python script executes with the permissions of the runtime process and may access resources available to that process unless the host environment applies stronger isolation.

## Operator guidance

- Review every skill, prompt, schema, and script before execution.
- Run the project with a least-privileged operating-system account or container.
- Keep model endpoint tokens in environment variables and out of prompts, traces, and committed files.
- Treat `skill_agent_context.json`, `trace.jsonl`, generated CSV files, and reports as potentially sensitive.
- Do not expose a local model endpoint to untrusted networks without authentication and transport protection.
- Delete or sanitize run artifacts before sharing them.

## Relevant vulnerability classes

Security reports are especially useful for:

- escaping the skill-root path boundary;
- executing undeclared commands or invoking a shell;
- bypassing branch or schema validation in a way that changes execution;
- leaking secrets through artifacts, traces, or model requests;
- unsafe handling of malicious `FLOWSCRIPT.md`, JSON, or generated files;
- dependency vulnerabilities that are reachable in this project.

Expected MVP limitations documented in the README, without an additional security impact, are not generally vulnerabilities.