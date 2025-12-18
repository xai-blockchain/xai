# ArgoCD GitOps Setup

## Installation Summary

ArgoCD installed on k3s cluster for GitOps-based deployments.

**Cluster**: k3s v1.33.6 (nodes: bcpc-staging, wsl2-worker)
**Namespace**: argocd (PSS: privileged)
**Version**: Latest stable from argoproj.io

## Access

**Web UI**: http://100.91.253.108:30085 (NodePort)
**Username**: admin
**Password**: `3hXOyOJFUrJ7keH7` (initial - change after first login)

## CLI Access

```bash
# Get password
sudo kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d

# Install argocd CLI (optional)
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

# Login
argocd login 100.91.253.108:30085 --username admin --insecure
```

## Sample Application

Located at `/home/hudson/blockchain-projects/xai/k8s/argocd-app-xai.yaml`

**Note**: Template requires repo credentials for private GitHub repos. Configure via:
- SSH keys in ArgoCD settings, OR
- GitHub token in repo credentials, OR
- Make repo public

Apply: `sudo kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml apply -f k8s/argocd-app-xai.yaml`

## Verification

All components running and healthy. Check status:
```bash
sudo kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml get all -n argocd
sudo kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml get applications -n argocd
```
