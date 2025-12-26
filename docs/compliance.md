# XAI Compliance Documentation

This document outlines XAI blockchain's compliance framework, covering data protection, KYC/AML integration, data retention, and jurisdiction considerations.

## GDPR Data Handling

### Personal Data Categories

XAI processes the following personal data categories:

| Category | Examples | Legal Basis |
|----------|----------|-------------|
| Wallet addresses | XAI addresses | Contract performance |
| Transaction data | Amounts, timestamps | Contract performance |
| Device tokens | Push notification tokens | Consent |
| IP addresses | API request origins | Legitimate interest |
| API keys | Authentication tokens | Contract performance |

### Data Subject Rights

XAI supports all GDPR data subject rights:

**Right of Access (Article 15)**
- Users can request all personal data via `/account/data-export`
- Response provided within 30 days

**Right to Rectification (Article 16)**
- Off-chain metadata can be corrected
- On-chain data is immutable by design (documented in terms)

**Right to Erasure (Article 17)**
- Off-chain data: Fully deletable
- On-chain transactions: Cannot be deleted (blockchain immutability)
- Users informed of this limitation during onboarding

**Right to Data Portability (Article 20)**
- Transaction history exportable in JSON format
- Wallet data exportable for migration

### Data Minimization

XAI follows data minimization principles:

- Only essential data collected for blockchain operations
- No unnecessary personal identifiers stored on-chain
- Wallet addresses are pseudonymous
- Optional fields clearly marked

### Consent Management

```python
# Consent collection example
{
    "consent_type": "push_notifications",
    "granted": true,
    "timestamp": 1704067200,
    "version": "1.0",
    "withdrawable": true
}
```

Consent can be withdrawn via:
- DELETE `/notifications/unregister`
- Account settings in wallet apps

---

## KYC/AML Integration Points

### Verification Levels

XAI supports tiered verification:

| Level | Requirements | Limits |
|-------|--------------|--------|
| 0 - Anonymous | None | Small transactions only |
| 1 - Basic | Email verification | Standard limits |
| 2 - Verified | Government ID + selfie | Enhanced limits |
| 3 - Enhanced | Source of funds | Unlimited |

### Integration Architecture

```
User -> XAI Wallet -> KYC Provider API -> Verification Result
                          |
                          v
               XAI Blockchain (stores only hash)
```

### KYC Data Flow

1. User initiates KYC via wallet app
2. Wallet redirects to third-party KYC provider
3. Provider performs verification
4. Provider returns verification result to XAI
5. XAI stores verification status (not documents)

**Stored on XAI:**
- Verification status hash
- Verification level
- Verification timestamp
- Provider reference ID

**NOT stored on XAI:**
- Identity documents
- Biometric data
- Government ID numbers

### Supported KYC Providers

- Jumio
- Onfido
- Sumsub
- Veriff

### AML Screening

XAI integrates with AML screening services:

**Transaction Monitoring:**
```python
# Fraud detection endpoint
POST /algo/fraud-check
{
    "payload": {
        "sender": "XAI...",
        "recipient": "XAI...",
        "amount": 10000
    }
}
```

**Sanctions List Screening:**
- OFAC SDN List
- EU Consolidated List
- UN Sanctions List
- PEP databases

**Suspicious Activity Indicators:**
- Rapid high-value transfers
- Known mixing service patterns
- Unusual transaction timing
- Velocity rule violations

### Travel Rule Compliance

For transactions above threshold:

```json
{
    "originator": {
        "name": "Required for transfers > threshold",
        "address": "Physical address",
        "account_number": "XAI..."
    },
    "beneficiary": {
        "name": "Required for transfers > threshold",
        "account_number": "XAI..."
    }
}
```

---

## Data Retention Policies

### Retention Periods

| Data Type | Retention Period | Justification |
|-----------|------------------|---------------|
| Blockchain data | Permanent | Immutable ledger |
| API logs | 90 days | Security monitoring |
| Device tokens | Until unregistered | Service provision |
| Failed transaction attempts | 30 days | Fraud prevention |
| Session data | 24 hours | Authentication |
| Rate limit data | 1 hour | Abuse prevention |

### Automatic Deletion

Expired data is automatically purged:

```python
# Automatic cleanup configuration
{
    "api_logs": {"retention_days": 90, "cleanup_frequency": "daily"},
    "session_data": {"retention_hours": 24, "cleanup_frequency": "hourly"},
    "rate_limit_data": {"retention_minutes": 60, "cleanup_frequency": "hourly"},
    "failed_attempts": {"retention_days": 30, "cleanup_frequency": "daily"}
}
```

### Blockchain Data

On-chain data cannot be deleted due to blockchain immutability. This is:
- Clearly disclosed in terms of service
- Documented in privacy policy
- Communicated during user onboarding

Users should not include personal data in transaction metadata.

### Backup and Recovery

- Off-chain data backed up daily
- Backups encrypted at rest (AES-256)
- Backups retained for 30 days
- Geographic redundancy (optional)

---

## Jurisdiction Considerations

### Supported Jurisdictions

XAI is designed to operate in jurisdictions with:
- Clear cryptocurrency regulations
- No blanket cryptocurrency bans
- Established AML frameworks

### Jurisdiction-Specific Features

**European Union (GDPR):**
- Full GDPR compliance
- Data processing agreements available
- EU-based data storage option

**United States:**
- FinCEN compliance for MSB activities
- State-by-state licensing awareness
- Sanctions compliance (OFAC)

**United Kingdom:**
- FCA registration support
- UK GDPR compliance
- Travel Rule compliance

**Switzerland:**
- FINMA guidelines compliance
- Self-regulatory organization membership support

### Restricted Jurisdictions

XAI implements geo-restrictions for:
- OFAC sanctioned countries
- Jurisdictions with cryptocurrency bans
- Regions specified by operators

### IP-Based Controls

```python
# Jurisdiction check middleware
{
    "blocked_countries": ["XX", "YY"],
    "restricted_features": {
        "ZZ": ["faucet", "high_value_transfers"]
    }
}
```

---

## Compliance API Endpoints

### Verification Status

```
GET /compliance/verification/{address}
```

**Response:**
```json
{
    "address": "XAI...",
    "level": 2,
    "status": "verified",
    "verified_at": 1704067200,
    "expires_at": 1735689600
}
```

### Transaction Risk Score

```
GET /compliance/risk/{txid}
```

**Response:**
```json
{
    "txid": "0x...",
    "risk_score": 0.15,
    "risk_level": "low",
    "screening_result": "passed"
}
```

### Compliance Report Export

```
GET /compliance/report/{address}
POST /compliance/report/generate
```

---

## Audit Trail

XAI maintains comprehensive audit trails:

### Logged Events

- Account creation
- Verification level changes
- High-value transactions
- Administrative actions
- Security events
- Consent changes

### Log Format

```json
{
    "event_id": "uuid",
    "event_type": "verification_completed",
    "timestamp": 1704067200,
    "actor": "XAI_ADDRESS or system",
    "target": "XAI_ADDRESS",
    "details": {},
    "ip_address": "hashed",
    "compliance_relevant": true
}
```

### Log Retention

- Compliance-relevant logs: 7 years
- Security logs: 2 years
- General logs: 90 days

---

## Third-Party Compliance

### Data Processing Agreements

Required DPAs in place with:
- Cloud infrastructure providers
- KYC/AML service providers
- Analytics providers (if any)
- Push notification services

### Sub-processor List

Available at `/legal/subprocessors` (if using hosted service)

### Security Certifications

- SOC 2 Type II (target)
- ISO 27001 (target)
- PCI DSS (if handling fiat)

---

## Incident Response

### Data Breach Procedure

1. Detection and containment
2. Assessment of impact
3. Notification to supervisory authority (within 72 hours)
4. User notification (if high risk)
5. Remediation and documentation

### Contact

For compliance inquiries:
- Data Protection Officer: [Configured per deployment]
- Compliance Team: [Configured per deployment]

---

## Regulatory Reporting

### Suspicious Activity Reports

XAI supports SAR filing for operators:
- Automated flagging of suspicious patterns
- SAR template generation
- Regulatory deadline tracking

### Currency Transaction Reports

For transactions above reporting thresholds:
- Automated CTR preparation
- Batch filing support
- Archive and retrieval

---

## Updates and Versioning

This document version: 1.0.0
Last updated: 2024-01-01

Compliance policies are reviewed quarterly and updated as regulations evolve.
