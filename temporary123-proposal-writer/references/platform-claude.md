# Claude adapter

Use the shared `SKILL.md` and [ordered workflow](proposal-workflow.md) for all proposal decisions. This file supplies Claude host conventions only. Do not maintain a second proposal workflow or pricing/specification library.

## Claude chat

Upload the generated `temporary123-proposal-writer.zip` through Claude's custom-skill upload interface, enable the skill and enable code execution/file creation. The archive has one enclosing `temporary123-proposal-writer` folder containing `SKILL.md` and all runtime resources. Connect authorized Drive/browser sources when available; the bundled resources are offline fallbacks, not a mirror of the whole Drive repository.

Skill selection is contextual, not an autonomous URL monitor. Ask explicitly to use Temporary 123 Proposal Writer when selection needs help. After a repository update, rebuild/re-upload the ZIP; a GitHub push alone does not prove that an installed Claude chat skill has changed.

Use available native document/file capabilities first, then the portable [Word helpers](word-workflow.md). Write outputs into the host's supported file-output directory (commonly `/mnt/data/output` when that environment exposes it), and verify the real saved path. Do not emit Codex-specific citation directives or assume a Codex Documents skill exists.

## Claude Code

Install the complete skill through `python tools/manage.py install --agent claude --scope user`, or use project scope for the current target project. Standard locations are `~/.claude/skills/temporary123-proposal-writer/` and `.claude/skills/temporary123-proposal-writer/`. Invoke `/temporary123-proposal-writer <opportunity URL>` or let normal contextual skill selection operate.

The repository's root `CLAUDE.md` imports `AGENTS.md` for shared repository instructions; those entrypoints do not replace installation of the complete skill. Keep installed copies as deployments and make future changes in the canonical repository.

Use the requested workspace/output directory and return actual file paths/links. Claude Code does not automatically have Claude chat's native document capabilities; use permitted installed dependencies and portable helpers when needed. Do not open desktop Word or assume a specific operating system or another user's absolute paths.

## Claude API

The host application must supply retrieval/Drive/browser tools or the needed source files, enable code execution and preinstall required dependencies. Do not assume network access or attempt package-install loops in an isolated container. The skill itself supplies neither tools nor credentials. The portable runtime is kept below the documented 30 MB uncompressed skill-upload limit; the unchanged large original price book remains in the repository archive while the complete reading copy is included.

## File sharing and final response

Use Claude's real file attachment/output-link mechanism where applicable. Follow [delivery-report.md](delivery-report.md) for the saved `.docx`, public Viewer link, page-by-page updates, submission readiness and winning analysis. A session attachment alone is not a verified Anyone-with-link URL. Use supported authorized cloud/browser capabilities for that setting; report a capability/policy failure honestly. Do not substitute company-only sharing or publish source files.

## Official references

- [Claude: custom skill packaging](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [Claude Code: skill locations and invocation](https://code.claude.com/docs/en/skills)
- [Claude Code: CLAUDE.md and AGENTS.md](https://code.claude.com/docs/en/memory)
- [Claude API: skills and limits](https://platform.claude.com/docs/en/build-with-claude/skills-guide)
