# Release Artifacts Policy

This repository is source-only. Do not commit compiled binaries, build outputs, or release artifacts to git.

Release artifacts must be published via GitHub Releases (or equivalent) with checksums and signatures.

Example:
```
sha256sum mybinary > SHA256SUMS
gpg --detach-sign --armor SHA256SUMS
# or
cosign sign-blob --yes SHA256SUMS
```
