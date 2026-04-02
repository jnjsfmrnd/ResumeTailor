# Contract Version Registry

**Owner**: Platform Lead
**Last Updated**: 2026-04-01

All shared contracts are frozen at the version recorded here. Any field or interface change requires:

1. A semver bump in this file.
2. A change note in the relevant contract file.
3. Platform Lead approval before merge.

## Versioned Contracts

| Contract File | Version | Status | Owner | Last Changed |
|---|---|---|---|---|
| `session-schema.md` | v1.0.0 | Frozen | Engineer A | 2026-04-01 |
| `section-output-schema.md` | v1.0.0 | Frozen | Engineer B | 2026-04-01 |
| `cover-letter-draft-schema.md` | v1.0.0 | Frozen | Engineer D | 2026-04-01 |
| `generation-service-interface.md` | v1.0.0 | Frozen | Engineer C | 2026-04-01 |
| `export-service-interface.md` | v1.0.0 | Frozen | Engineer D | 2026-04-01 |

## Change Control Rules

- **PATCH** (x.x.N): Non-breaking addition of optional field or clarifying note.
- **MINOR** (x.N.0): Backward-compatible addition of required field with default.
- **MAJOR** (N.0.0): Breaking change — removal, rename, or type change of any field.

Any MAJOR or MINOR bump requires platform lead sign-off and a migration note in the contract file.
Any lane that consumes a changed contract must update its implementation to match before merge.
