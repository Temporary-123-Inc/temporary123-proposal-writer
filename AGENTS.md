# Repository instructions

## Proposal requests

For a solicitation/project link or a request to write a Temporary 123 proposal, read and follow [the canonical skill](temporary123-proposal-writer/SKILL.md). Its shared references are the authority for proposal workflow, pricing, specifications, images, Word QA, and delivery. Do not reproduce those rules in a platform-specific instruction file.

When running in Codex, also read [the Codex adapter](temporary123-proposal-writer/references/platform-codex.md). Other hosts should use their matching adapter. Resolve bundled resources from the canonical skill directory rather than a machine-specific installation path.

## Repository maintenance

- Maintain one installable `temporary123-proposal-writer/` folder. Change shared behavior in its `SKILL.md` or shared references; use platform adapters only for host-specific capabilities and invocation.
- Keep pricing, specifications, inventory data, assets, and scripts in that shared folder. Do not create parallel Codex/Claude source trees or separate platform ZIPs.
- Preserve original sources and provenance. The original price book belongs in `source-archives/`; the portable reading copy belongs in the runtime assets. Review source refreshes and regenerate derived data only within the user's authorized scope.
- Treat the original inventory workbook as an internal source. Use the technical index for routine specification lookup and keep operational/access/client/driver/tracker data out of buyer documents.
- Keep proposal drafts, scratch inputs, rendered QA pages, local environments, and `dist/` artifacts out of Git. Run document work in the task workspace outside the installed skill.
- Do not change source/folder sharing, submit bids, send outreach, or publish unrelated material as a side effect of maintenance. Apply proposal-output sharing only under the canonical workflow's authorization and verify the actual result.

Before publishing a change, run from the repository root:

```sh
python tools/manage.py validate
python -m unittest discover -s tests -v
python tools/manage.py package --output dist/temporary123-proposal-writer.zip
```

Review failures and the resulting package before release. A successful local validation, package build, or install does not prove live platform activation or successful proposal execution; report only checks actually performed.

Use [docs/commands.md](docs/commands.md) for command details and [docs/architecture.md](docs/architecture.md) for file ownership.
