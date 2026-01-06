# Release Process

This repo is source-only. Release artifacts must be published via GitHub Releases with checksums and signatures.

## Versioning
- Use semantic versioning: `vMAJOR.MINOR.PATCH`.
- Tag releases with annotated tags.

## Checklist
1. Create a release PR from a clean branch.
2. Ensure CI is green.
3. Build from a clean checkout (see `DEVELOPMENT.md`).
4. Produce artifacts, `SHA256SUMS`, and signatures (see `RELEASE_ARTIFACTS.md`).
5. Create a GitHub Release with notes and attach artifacts + `SHA256SUMS` + signatures.
6. Verify downloads match published checksums.
