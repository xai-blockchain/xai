# Bridge Security

This repository does not ship a production cross-chain bridge.
Cross-chain utilities in this repo (for example, atomic swap tooling) are
for development and testing only.

Any bridge deployment should include:
- Independent security review of bridge contracts and relayers
- Monitoring, rate limits, and emergency pause controls
- Separate key management and signing policies
