# Linkerd mTLS Setup for XAI Validators

## Installation Summary

Linkerd service mesh installed on k3s cluster to provide automatic mTLS between pods.

## Prerequisites

- Gateway API CRDs v1.4.0
- Privileged PSS enforcement for namespaces with Linkerd-meshed pods
- Network egress policy allowing traffic to `linkerd` namespace

## Installation Steps

```bash
# Install Linkerd CLI
curl -sL https://run.linkerd.io/install-edge | sh
export PATH=$PATH:~/.linkerd2/bin

# Install Gateway API CRDs
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.0/standard-install.yaml

# Install Linkerd control plane
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -

# Verify installation
linkerd check
```

## Mesh Configuration for XAI Namespace

```bash
# Enable Linkerd injection on namespace
kubectl annotate namespace xai linkerd.io/inject=enabled --overwrite

# Remove webhook disabled label
kubectl label namespace xai config.linkerd.io/admission-webhooks-

# Set PSS to privileged (required for linkerd-init container)
kubectl label namespace xai pod-security.kubernetes.io/enforce=privileged --overwrite

# Update network egress policy to allow Linkerd traffic
kubectl patch networkpolicy xai-egress-policy -n xai --type json -p='[{"op": "add", "path": "/spec/egress/-", "value": {"to": [{"namespaceSelector": {"matchLabels": {"linkerd.io/is-control-plane": "true"}}}]}}]'
```

## Verification

```bash
# Check proxies are injected (should show 2/2 containers)
kubectl get pods -n xai

# Verify mTLS certificates
linkerd check --proxy -n xai

# Check proxy logs for certified identity
kubectl logs -n xai <pod-name> -c linkerd-proxy | grep "Certified identity"
```

## Notes

- Pods show 2/2 containers when meshed (app container + linkerd-proxy)
- Each pod receives a unique mTLS identity: `<serviceaccount>.<namespace>.serviceaccount.identity.linkerd.cluster.local`
- All pod-to-pod traffic within meshed namespaces is automatically encrypted
