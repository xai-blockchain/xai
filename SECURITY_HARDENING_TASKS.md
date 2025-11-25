<!--
This file captures every outstanding SECURITY REVIEW CHECKLIST TODO.
Each task is declared explicitly so downstream engineers know exactly what must be implemented.
Update the `Status` column as you work through a task: "todo" → "in progress" → "done".
-->

# Security Hardening Master TODO List

| # | Task | Section Reference | Status | Notes / Acceptance |
|---|------|-------------------|--------|--------------------|
| 1 | Add hardware wallet integration | SECURITY_REVIEW_CHECKLIST.md (lines 30-139) | done | Wallets can now be hardware-backed (`HardwareWallet` interface + `Wallet` passthrough) and `tests/xai_tests/unit/test_hardware_wallet_integration.py` covers the behavior. |
| 2 | Add nonce-based replay protection | SECURITY_REVIEW_CHECKLIST.md (line 52) | done | `tests/xai_tests/unit/test_nonce_and_timestamp_hardening.py` covers replay rejections and sequential enforcement using `NonceTracker`. |
| 3 | Add timestamp drift validation | SECURITY_REVIEW_CHECKLIST.md (line 73) | done | Timestamp validation already enforces ±2-hour drift and `tests/xai_tests/unit/test_nonce_and_timestamp_hardening.py` ensures out-of-range inputs fail. |
| 4 | Add validation for time capsule reserve balance | SECURITY_REVIEW_CHECKLIST.md (line 146) | todo | Prevent withdrawals that violate reserve rules. |
| 5 | Prevent reserve wallet from being drained | SECURITY_REVIEW_CHECKLIST.md (line 147) | todo | Add circuit breaker / max withdrawal per period. |
| 6 | Add peer reputation system | SECURITY_REVIEW_CHECKLIST.md (line 156) | todo | Score peers based on behavior; use it for routing. |
| 7 | Implement connection limits | SECURITY_REVIEW_CHECKLIST.md (line 157) | todo | Cap total inbound/outbound peers per node. |
| 8 | Add DDoS protection | SECURITY_REVIEW_CHECKLIST.md (line 158) | todo | Rate-limit messages, drop suspicious traffic. |
| 9 | Validate peer messages | SECURITY_REVIEW_CHECKLIST.md (line 159) | todo | Enforce protocol sanity checks before processing. |
|10 | Add authentication (optional) | SECURITY_REVIEW_CHECKLIST.md (line 164) | todo | Add optional API/mgmt auth for privileged endpoints. |
|11 | Prevent injection attacks | SECURITY_REVIEW_CHECKLIST.md (line 166) | todo | Sanitize inputs before passing to other systems. |
|12 | Amount validation (prevent negative/overflow) | SECURITY_REVIEW_CHECKLIST.md (line 176) | todo | Enforce amount sanity in transactions. |
|13 | Fee validation (prevent excessive fees) | SECURITY_REVIEW_CHECKLIST.md (line 177) | todo | Ensure fees stay within protocol-defined ranges. |
|14 | Address format validation | SECURITY_REVIEW_CHECKLIST.md (line 178) | todo | Reject malformed destination addresses. |
|15 | Validate all JSON inputs | SECURITY_REVIEW_CHECKLIST.md (line 181) | todo | Use schema checks before accepting requests. |
|16 | Sanitize user inputs | SECURITY_REVIEW_CHECKLIST.md (line 182) | todo | Strip dangerous characters from UI/CLI inputs. |
|17 | Prevent SQL injection (if database added) | SECURITY_REVIEW_CHECKLIST.md (line 183) | todo | Use parameterized queries for every DB path. |
|18 | Prevent XSS (if web interface added) | SECURITY_REVIEW_CHECKLIST.md (line 184) | todo | Encode/sanitize data rendered in web views. |
|19 | Limit input sizes | SECURITY_REVIEW_CHECKLIST.md (line 185) | todo | Cap payload lengths at entry points. |
|20 | Never expose internal errors to users | SECURITY_REVIEW_CHECKLIST.md (line 193) | todo | Hide stack traces; return sanitized diagnostics. |
|21 | Log errors securely | SECURITY_REVIEW_CHECKLIST.md (line 194) | todo | Mask secrets in logs; enforce redaction policies. |
|22 | Fail securely (don't expose sensitive data) | SECURITY_REVIEW_CHECKLIST.md (line 195) | todo | Ensure panic paths clear auth/session data. |
|23 | Professional security audit | SECURITY_REVIEW_CHECKLIST.md (line 209) | todo | Engage third-party auditor and log findings. |
|24 | Penetration testing | SECURITY_REVIEW_CHECKLIST.md (line 210) | todo | Run red-team exercises against nodes and APIs. |
|25 | Code review by security experts | SECURITY_REVIEW_CHECKLIST.md (line 211) | todo | Have dedicated security reviewers inspect changes. |
|26 | Bug bounty program | SECURITY_REVIEW_CHECKLIST.md (line 212) | todo | Launch bounty with clear scope & triage workflow. |
|27 | Integration tests | SECURITY_REVIEW_CHECKLIST.md (line 223) | todo | Write high-fidelity tests combining modules. |
|28 | Load testing | SECURITY_REVIEW_CHECKLIST.md (line 224) | todo | Run load suites to confirm scalability. |
|29 | Security testing | SECURITY_REVIEW_CHECKLIST.md (line 225) | todo | Run static/dynamic scans on builds. |
|30 | Penetration testing | SECURITY_REVIEW_CHECKLIST.md (line 226) | todo | Repeat periodic pen-tests (different focus). |
|31 | Verify genesis hash consistency | SECURITY_REVIEW_CHECKLIST.md (line 242) | todo | Compare hashes across deployments. |
|32 | Distribute genesis file securely | SECURITY_REVIEW_CHECKLIST.md (line 243) | todo | Sign & verify genesis during bootstrapping. |
|33 | Prevent genesis manipulation | SECURITY_REVIEW_CHECKLIST.md (line 244) | todo | Lock genesis configs (e.g., git LFS with checksum). |
|34 | Create secure deployment scripts | SECURITY_REVIEW_CHECKLIST.md (line 247) | todo | Harden CI/CD scripts, avoid leaking secrets. |
|35 | Environment variable validation | SECURITY_REVIEW_CHECKLIST.md (line 248) | todo | Reject invalid/missing critical env vars. |
|36 | Secure defaults | SECURITY_REVIEW_CHECKLIST.md (line 249) | todo | Default to hardened modes (no debug, minimal exposure). |
|37 | Production hardening | SECURITY_REVIEW_CHECKLIST.md (line 250) | todo | Document & enforce network/service hardening. |
|38 | Code signing | SECURITY_REVIEW_CHECKLIST.md (line 339) | todo | Sign binaries/artifacts before release. |
|39 | Dependency security scanning | SECURITY_REVIEW_CHECKLIST.md (line 340) | todo | Add SBOM scanning + vulnerabilities alerts. |
|40 | Secure deployment process | SECURITY_REVIEW_CHECKLIST.md (line 343) | todo | Verify gating steps (approval, rollback). |
|41 | Monitoring and alerting | SECURITY_REVIEW_CHECKLIST.md (line 344) | todo | Signal key metrics and intrusions. |
|42 | Incident response plan | SECURITY_REVIEW_CHECKLIST.md (line 345) | todo | Document roles/processes for incidents. |
|43 | Backup and recovery | SECURITY_REVIEW_CHECKLIST.md (line 346) | todo | Strengthen backup retention + restore playbooks. |
|44 | Update/patch process | SECURITY_REVIEW_CHECKLIST.md (line 347) | todo | Track dependencies, schedule patch windows. |
|45 | User security guidelines | SECURITY_REVIEW_CHECKLIST.md (line 350) | todo | Publish secure usage guidance for operators. |
|46 | Wallet backup instructions | SECURITY_REVIEW_CHECKLIST.md (line 351) | todo | Document safe wallet backup/restore. |
|47 | Phishing prevention guidance | SECURITY_REVIEW_CHECKLIST.md (line 352) | todo | Train users to detect phishing/typosquats. |
|48 | Best practices documentation | SECURITY_REVIEW_CHECKLIST.md (line 353) | todo | Consolidate all hardening docs for devs/ops. |
