# Architecture

## One repository, one runtime

[Temporary-123-Inc/temporary123-proposal-writer](https://github.com/Temporary-123-Inc/temporary123-proposal-writer) is the maintained source for both platforms. The repository separates contributor guidance and original archives from the portable skill:

```text
temporary123-proposal-writer/             repository root
├── AGENTS.md                            shared maintenance and Codex routing
├── CLAUDE.md                            native @AGENTS.md import and Claude routing
├── README.md
├── docs/                                installation, commands, architecture
├── tools/manage.py                      validate, package, install, doctor
├── tests/                               management-tool verification
├── source-archives/                     original price book; repository only
└── temporary123-proposal-writer/         sole installable runtime
    ├── SKILL.md                         canonical workflow and reference routing
    ├── agents/openai.yaml               Codex metadata and invocation policy
    ├── references/
    │   ├── platform-codex.md            Codex capabilities and fallbacks
    │   ├── platform-claude.md           Claude capabilities and fallbacks
    │   └── …                           shared proposal and source rules
    ├── assets/                         one shared source and output-asset set
    └── scripts/                        inventory and portable Word helpers
```

The release ZIP contains only the installable runtime folder. Repository documentation, Git history, CI, tests, management tooling, generated proposals, and the original archive do not become runtime dependencies.

## Instruction ownership

| Layer | Responsibility |
| --- | --- |
| [SKILL.md](../temporary123-proposal-writer/SKILL.md) | Skill selection, essential workflow, and shared-reference routing. |
| [Shared references](../temporary123-proposal-writer/references/proposal-workflow.md) | Proposal order, evidence, pricing, product selection, inventory, Word work, and final delivery rules. |
| [Codex adapter](../temporary123-proposal-writer/references/platform-codex.md) / [Claude adapter](../temporary123-proposal-writer/references/platform-claude.md) | Host-specific discovery, tools, invocation, and fallback behavior. |
| [AGENTS.md](../AGENTS.md) / [CLAUDE.md](../CLAUDE.md) | Repository maintenance and native platform entrypoints. |
| `tools/manage.py` | Deterministic repository checks, installation, packaging, and local diagnostics. |

Change a business rule once in the canonical skill or its shared reference. An adapter can explain how to perform that rule in its host; it must not establish a second pricing or proposal workflow. Preserve `agents/openai.yaml`'s implicit invocation policy unless the user changes it.

## Sources and derived data

The current 19-page price book was supplied November 15, 2026. Its raw original remains outside Git because page 17 contains confidential tax identifiers. `source-archives/temporary123-rental-price-book-2026-11-15-sanitized.pdf` and runtime `assets/rental-price-book-reading-copy.pdf` replace that whole page and retain all 19 page positions. The searchable text includes manually verified image-page pricing content. The normalized `assets/pricing/rate-catalog.json` and `references/rental-pricing-guide.md` distinguish published values, unresolved rental units and the user-approved per-visit/two-visits-month service policy. `scripts/pricing.py` calculates explicit source-backed lines and supported partial subtotals. The earlier unchanged 15-page source remains in `source-archives/temporary123-rental-price-book.pdf` as legacy provenance. Other retained assets include the original proposal/cover-letter and style references, company documents, image catalog, approved images, inventory workbook, and technical index.

The original inventory is a November 3, 2026 snapshot with 174 records, of which 173 have names. Its technical JSON helper retains ItemIDs and workbook cell locators and excludes operational/access/client/driver/tracker fields. The original workbook remains internal evidence. Neither a snapshot nor a model photograph establishes current availability. Consult [inventory specifications](../temporary123-proposal-writer/references/inventory-specifications.md) for interpretation and conflict handling.

Source hashes, dates, limitations, and transformations are recorded in [source provenance](../temporary123-proposal-writer/assets/source-provenance.json). Refresh evidence only with authorized sources, then review derived-data and provenance changes together. Keep pricing and technical authority as defined in the shared references.

## Portability and verification

One ZIP serves Codex and Claude; repository-only archives are excluded to keep the portable package within Claude's 30 MB API skill limit and OpenAI's 25 MB per-file limit. `package` applies the repository's size and content checks before writing the artifact.

Use the host's available document capability first. The packaged Python fallback needs `python-docx`, image work uses `Pillow`, and PDF reading uses `pypdf`. Rendering additionally needs headless LibreOffice and a PDF rendering backend. These are host prerequisites, not bundled installations. See [installation](installation.md) and the [Word workflow](../temporary123-proposal-writer/references/word-workflow.md).

CI validates the repository, runs management-tool tests, and builds the portable ZIP with read-only repository permissions. It does not access private company services, share source files, send messages, submit proposals, deploy software, or establish live platform activation.
