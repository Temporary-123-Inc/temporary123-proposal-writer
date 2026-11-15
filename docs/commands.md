# Commands

Run repository commands from the cloned repository root. Python 3.12 is the CI baseline. If `python` is unavailable or resolves to a Windows Store alias, use the full path to an installed Python 3 interpreter; Codex can locate its bundled runtime through its dependency loader. Management and inventory commands use the standard library; proposal authoring and rendering have additional [prerequisites](installation.md).

## Validate, test, and package

```sh
python tools/manage.py validate
python -m unittest discover -s tests -v
python tools/manage.py package --output dist/temporary123-proposal-writer.zip
```

Validation checks repository/runtime consistency, relative documentation links, and bundled asset integrity. Tests exercise management behavior. Packaging creates one ZIP with the `temporary123-proposal-writer/` root folder and excludes repository-only archives and generated content. Review command output; passing these checks does not prove live host activation or visual proposal quality.

Use command help for the installed version's full options:

```sh
python tools/manage.py --help
python tools/manage.py install --help
```

## Install

```sh
python tools/manage.py install --agent codex --scope user
python tools/manage.py install --agent codex --scope project
python tools/manage.py install --agent claude --scope user
python tools/manage.py install --agent claude --scope project
```

| Target | User default | Project default |
| --- | --- | --- |
| Codex | `~/.agents/skills/temporary123-proposal-writer` | `.agents/skills/temporary123-proposal-writer` |
| Claude Code | `~/.claude/skills/temporary123-proposal-writer` | `.claude/skills/temporary123-proposal-writer` |

`--skills-dir` selects a skills root; the installer places the named skill folder beneath it. Use `--overwrite` deliberately when updating an existing installation. For this workspace's existing configured Codex skills root:

```sh
python tools/manage.py install --agent codex --scope user --skills-dir C:/Users/Admin/.codex/skills --overwrite
```

Other users should use their own configured root or the default. Project scope resolves from the current working directory. See [installation](installation.md) for ZIP installation and platform activation.

## Diagnose the environment

```sh
python tools/manage.py doctor
```

Read the reported paths and available dependencies before choosing a workflow. Diagnostics do not install software, connect accounts, grant permissions, or activate a skill in a host session.

## Look up prices and calculate quotes

```sh
python temporary123-proposal-writer/scripts/pricing.py find --query shower --limit 5
python temporary123-proposal-writer/scripts/pricing.py show --id combo-13ft-3-stall
python temporary123-proposal-writer/scripts/pricing.py quote --input /absolute/path/quote-request.json
```

The [pricing guide](../temporary123-proposal-writer/references/rental-pricing-guide.md) explains the catalog and units. A request contains a `lines` array. Rental lines use `item_id`, `rate_key`, `quantity` and `periods`; service `per_visit` lines use explicit `visits`, or whole `months` for the standing two-visits/month recommendation when the contract is silent. Unknown requested rates produce an incomplete result with a known subtotal and no final total. These calculations do not establish that all required charges are present, equipment is available or the quote complies with the buyer's requirements.

```json
{"lines":[{"item_id":"combo-13ft-3-stall","rate_key":"month","quantity":1,"periods":4},{"item_id":"pump-restroom-300","rate_key":"per_visit","quantity":1,"months":4}]}
```

Use actual service units rather than copying trailer count automatically. If the same restroom pump-out is included in a shower-bladder visit, identify the shared `coverage_group` and remove duplicate charges. Do not derive daily or unspecified portable rental periods. Partial months need an explicit approved billing basis or actual visit count.

## Look up inventory

```sh
python temporary123-proposal-writer/scripts/inventory.py find --query restroom --limit 5
python temporary123-proposal-writer/scripts/inventory.py show --item-id ITEM_ID_FROM_FIND
python temporary123-proposal-writer/scripts/inventory.py verify
```

Copy the actual `item_id` from `find` into `show`. Retain workbook cell locators when using a technical claim. `verify` compares the index to the retained source workbook; it does not contact live inventory or confirm availability.

After an authorized source refresh, retain the reviewed workbook at `temporary123-proposal-writer/assets/inventory/temporary123-inventory-and-specifications.xlsx`, preserving any prior source needed for audit. Rebuild against that retained source:

```sh
python temporary123-proposal-writer/scripts/inventory.py build
python temporary123-proposal-writer/scripts/inventory.py verify
```

Review changed facts and identity conflicts. In `assets/source-provenance.json`, update the inventory snapshot date, counts and original/index SHA-256 values from the reviewed source/index metadata, plus both inventory entries in `bundled_asset_sha256`. Run repository validation before packaging; it rejects stale indexes and mismatched hashes. Do not simply approve a new manifest hash to bypass a content discrepancy. A successful rebuild does not confirm current availability.

## Portable Word helpers

Prefer the current host's document tools when available. Use the packaged fallback according to the [Word workflow](../temporary123-proposal-writer/references/word-workflow.md). Keep the task's content JSON, documents, calculations, and QA output outside the installed skill and Git:

```sh
python temporary123-proposal-writer/scripts/create_proposal.py --schema
python temporary123-proposal-writer/scripts/create_proposal.py task/proposal-content.json --output task/Proposal_Draft.docx
python temporary123-proposal-writer/scripts/inspect_proposal.py task/Proposal_Draft.docx --require-cover-letter --expected-images 2
python temporary123-proposal-writer/scripts/render_proposal.py task/Proposal_Draft.docx --output-dir task/qa-pass-1
```

Supply the actual intended image count. These helpers compose supplied content and check document structure; they do not research an opportunity, approve prices, supply missing answers, or replace inspection of every rendered page. Use fresh QA directories for subsequent renders and follow the shared workflow before delivery.
