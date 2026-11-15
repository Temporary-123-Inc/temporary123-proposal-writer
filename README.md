# Temporary 123 Proposal Writer

One maintained proposal-writing skill for Codex and Claude. It turns a solicitation or rental-project link into an editable Word proposal with a personalized cover letter, supported pricing, equipment specifications, relevant images, and a clear delivery report.

The canonical repository is [Temporary-123-Inc/temporary123-proposal-writer](https://github.com/Temporary-123-Inc/temporary123-proposal-writer). Both platforms use the same [SKILL.md](temporary123-proposal-writer/SKILL.md), reference files, assets, data, and Python helpers. Platform adapters describe host capabilities; they do not carry separate proposal rules or source copies.

## Start here

- [Installation](docs/installation.md): Codex, Claude Code, and Claude.ai.
- [Commands](docs/commands.md): validation, packaging, installation, inventory lookup, and document helpers.
- [Architecture](docs/architecture.md): what belongs in the repository and the portable skill.
- [AGENTS.md](AGENTS.md): repository maintenance and the Codex entrypoint.
- [CLAUDE.md](CLAUDE.md): Claude Code entrypoint with a native shared-instruction import.

From the repository root, with Python 3.10+ (CI uses 3.12):

```sh
python tools/manage.py validate
python -m unittest discover -s tests -v
python tools/manage.py package --output dist/temporary123-proposal-writer.zip
```

The ZIP contains one `temporary123-proposal-writer/` folder. Use that same artifact for either platform; no platform-specific release copy is needed.

## Use the skill

After installation, invoke `$temporary123-proposal-writer` in Codex or `/temporary123-proposal-writer` in Claude Code, then provide the opportunity link. In Claude.ai, enable the uploaded skill and provide the link in a chat with the necessary code-execution and source access.

Read the [canonical workflow](temporary123-proposal-writer/SKILL.md) for source checks, required missing information, Word layout review, pricing support, and the final delivery report. It specifies **Link**, **What to update**, **Readiness**, and **Winning chances and improvements**. The generated Word output's public Viewer link must be verified before it is reported as publicly accessible; source files and folders retain their permissions.

## Included sources and limits

The runtime includes a [normalized rental/service pricing guide](temporary123-proposal-writer/references/rental-pricing-guide.md), [structured rate catalog](temporary123-proposal-writer/assets/pricing/rate-catalog.json), [pricing lookup/calculator](temporary123-proposal-writer/scripts/pricing.py), sanitized price-book reading copy and text extraction, original cover-letter/style sources, company documents, image catalog, approved restroom images, original inventory workbook, and a technical inventory index. The index covers **174 records, 173 named**, from the **November 3, 2026** inventory snapshot. It is technical evidence, not live availability. Operational, access, client, driver, and tracker fields stay out of the technical index and buyer-facing prose.

The current pricing source is the 19-page `Temporary123_Rental_Price_Book (8) 1.pdf`, supplied November 15, 2026. The runtime guide and JSON preserve its event (1-3 days), weekly, monthly and other explicit billing units. Standalone service prices use the user-approved per-visit basis, with two visits/month recommended only when the contract is silent. The new original contains confidential tax fields on page 17 and stays outside Git; sanitized repository/runtime PDFs replace that entire page while retaining page numbers. The older unchanged 15-page book remains in `source-archives/temporary123-rental-price-book.pdf` as historical evidence. Packaging checks the actual runtime size; repository archives are excluded from the installable ZIP.

Bundled records do not provide live solicitation access, current stock, current qualification, or connector credentials. Host tools and authorized sources supply those capabilities. No installer downloads dependencies automatically, and repository checks do not establish that a skill has been activated in a live Codex or Claude session.

## Maintain one source

Edit the canonical skill folder, validate it, run the tests, and package the result before publishing. Keep generated proposals, research inputs, QA output, and release ZIPs outside Git. See [architecture](docs/architecture.md) for the source/archive boundary and [commands](docs/commands.md) for checks.

## Migration from standalone versions

This repository preserves the former Codex and Claude skill histories and is the single maintained source. The former Codex repository URL redirects here; the old standalone Claude repository is archived with a migration pointer. Rebuild/install the unified package rather than updating those old platform trees.

If a skill is already installed, update its existing configured skills root using `--skills-dir` and `--overwrite` instead of creating a second same-named installation. Claude chat users should replace/re-upload the enabled custom skill from the unified ZIP; a repository push alone does not update a chat upload.
