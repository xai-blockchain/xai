# Cert-Manager for Kubernetes TLS

## Installation

Cert-manager v1.16.2 installed via official manifests. PSS exemption applied to cert-manager namespace.

## ClusterIssuers

**selfsigned-issuer**: Self-signed certificates for root CA
**ca-issuer**: CA-based issuer using `ca-key-pair` secret in cert-manager namespace

## Usage

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-cert
  namespace: xai
spec:
  secretName: my-tls
  issuerRef:
    name: ca-issuer
    kind: ClusterIssuer
  commonName: mydomain.local
  dnsNames:
    - mydomain.local
    - "*.xai.svc.cluster.local"
  duration: 2160h  # 90 days
  renewBefore: 720h  # 30 days before expiry
```

## Test Certificate

`xai-test-cert` deployed in xai namespace, stored in `xai-test-tls` secret. Covers:
- xai.local
- xai-rpc.xai.svc.cluster.local
- *.xai.svc.cluster.local

## Verification

```bash
kubectl -n xai get certificate
kubectl -n xai get secret xai-test-tls
kubectl get clusterissuers
```
