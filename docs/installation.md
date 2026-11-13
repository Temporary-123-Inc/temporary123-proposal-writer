# Installation

## Choose one runtime artifact

Clone [the canonical repository](https://github.com/Temporary-123-Inc/temporary123-proposal-writer) for maintenance or local installation. Build the portable upload artifact from the repository root:

```sh
python tools/manage.py validate
python tools/manage.py package --output dist/temporary123-proposal-writer.zip
```

Use the same ZIP for both platforms. It contains exactly one `temporary123-proposal-writer/` folder with `SKILL.md`, shared references, assets, scripts, and Codex metadata. Do not upload the repository root or add a second nesting folder. The repository-only original price-book archive is excluded; the complete portable source set uses the smaller reading copy.

## Codex

With Python 3.10+ available, run from the repository root:

```sh
python tools/manage.py install --agent codex --scope user
```

The default destination is `~/.agents/skills/temporary123-proposal-writer`. For a skill limited to the current project, use `--scope project`, which installs under `.agents/skills/`. If Codex is configured to discover another skills root, pass that root with `--skills-dir`; the installer appends the skill's folder name.

For this workspace's existing configuration only:

```sh
python tools/manage.py install --agent codex --scope user --skills-dir C:/Users/Admin/.codex/skills --overwrite
```

Use `--overwrite` when intentionally replacing an existing installation. After installation, make the skill available to a new or refreshed host session according to that host's behavior, invoke `$temporary123-proposal-writer`, and supply the opportunity link. The retained `agents/openai.yaml` preserves implicit discovery as well. Repository proposal requests route through [AGENTS.md](../AGENTS.md) and the [Codex adapter](../temporary123-proposal-writer/references/platform-codex.md).

See OpenAI's [Build skills guide](https://learn.chatgpt.com/docs/build-skills) and [AGENTS.md configuration guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md) for the supported host conventions.

## Claude Code

```sh
python tools/manage.py install --agent claude --scope user
```

The user default is `~/.claude/skills/temporary123-proposal-writer`; `--scope project` uses `.claude/skills/temporary123-proposal-writer`. For a custom root, use `--skills-dir ROOT`. Extracting the same ZIP directly into the appropriate skills root is an alternative.

Invoke `/temporary123-proposal-writer` and supply the opportunity link. When working in this repository, [CLAUDE.md](../CLAUDE.md) uses native `@AGENTS.md` import syntax for shared repository instructions and routes to the [Claude adapter](../temporary123-proposal-writer/references/platform-claude.md). User-installed skills do not depend on the repository's root instruction files.

See Claude Code's [skills documentation](https://code.claude.com/docs/en/skills) and [memory imports documentation](https://code.claude.com/docs/en/memory).

## Claude.ai

1. Build or obtain `dist/temporary123-proposal-writer.zip` from the canonical repository.
2. Enable code execution and file creation in the Claude environment, then upload the ZIP through its custom-skills interface.
3. Enable the skill and connect or provide access to the opportunity and company sources needed for the requested proposal.
4. Start a chat, provide the solicitation/project link, and request the proposal. Follow any required-input questions raised by the shared workflow.

The upload supplies instructions and bundled files. It does not connect private Drive accounts, supply connector credentials, create public sharing permissions, or install missing system tools. Check the current [custom-skills upload guide](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) and [Claude skills guide](https://platform.claude.com/docs/en/build-with-claude/skills-guide) for interface and API requirements.

## Runtime prerequisites

| Work | Required capability |
| --- | --- |
| Repository validation, packaging, installation, inventory lookup | Python 3.10+; management/inventory helpers use the standard library. CI uses 3.12. |
| Live research and company-source retrieval | Authorized browser or connected tools with access to the actual sources. |
| Word authoring | The host's native document capability, or Python with `python-docx`; image processing also needs `Pillow`. |
| PDF source reading | An available PDF tool or `pypdf` for the Python fallback. |
| Local document rendering | Headless LibreOffice plus `PyMuPDF`, `pypdfium2`, or Poppler; see the shared Word workflow for browser/Docs export recovery. |
| Public Word delivery | Authorized file storage and sharing tools that can save the actual `.docx` and verify its generated output's Viewer link. |

Run `python tools/manage.py doctor` to inspect local readiness. No installer or diagnostic command installs these dependencies automatically. Read [the Word workflow](../temporary123-proposal-writer/references/word-workflow.md) for supported fallbacks; platform access and tool availability still govern execution.

## Verify installation and updates

Run [validation and tests](commands.md) before packaging an update. Install into the intended root, then confirm the skill is discoverable in the target host and test an authorized proposal request with accessible sources. Record the actual checks and limitations. A copied folder, valid ZIP, or passing CI run establishes packaging behavior; live Codex/Claude activation and a complete proposal require their own observed checks.
