# Codex adapter

Use the shared `SKILL.md` and [ordered workflow](proposal-workflow.md) for all proposal decisions. This file supplies Codex host conventions only. Keep business rules, source facts and pricing in the shared references.

## Invocation and installation

Invoke `$temporary123-proposal-writer <opportunity URL>` or submit a link in the established proposal workflow. `agents/openai.yaml` keeps implicit invocation enabled. Install the complete skill folder, not just `SKILL.md`.

The repository management command supports `python tools/manage.py install --agent codex --scope user`; current documented user discovery uses `~/.agents/skills/`, with `.agents/skills/` for project scope. A configured or older Codex host may use a different skill directory. Use `--skills-dir PATH` for that actual skills root, and verify discovery in the target host rather than silently changing its configuration. Installed files are deployment copies; maintain the canonical repository and reinstall after changes.

## Tools and artifacts

Use the available Documents skill and its current instructions for native Word authoring, including any artifact marker and render requirements. Use the host's dependency loader for bundled runtimes when available. The portable [Word helpers](word-workflow.md) are the fallback when that capability is unavailable. No native desktop Word/COM/GUI takeover is authorized.

Prefer connected source tools and their applicable Docs/Drive/Sheets skills; use authorized browser access when a needed operation is absent from a connector. Tool availability and permission scopes vary. The skill does not supply credentials or grant connector access.

Use the actual host's artifact/file-citation format when required. The final **Link** must still refer to the saved Word output and its verified public Viewer access, following [delivery-report.md](delivery-report.md); a local file citation alone is not proof of public cloud sharing. Keep the other three delivery sections and source-status tracking exactly as the shared guide defines them.

## Official references

- [OpenAI: skills and discovery](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI: AGENTS.md instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
