# Anonymous GitHub Upload Guide

Step-by-step instructions for uploading XAI blockchain to GitHub anonymously.

## Prerequisites

1. **Tor Browser** - https://www.torproject.org/
2. **ProtonMail** - Create anonymous email via Tor
3. **Git** - Already installed

## Step 1: Create Anonymous GitHub Account

1. Open Tor Browser
2. Go to GitHub.com
3. Sign up with ProtonMail email
4. Use neutral username
5. **ONLY** access via Tor

## Step 2: Configure Git

```bash
cd /path/to/aixn
git config user.name "XAI Developer"
git config user.email "noreply@protonmail.com"
```

## Step 3: Initialize Repository

```bash
git init
git add .
git commit -m "Initial commit: XAI blockchain"
```

## Step 4: Create GitHub Repo (via Tor)

1. In Tor Browser: GitHub → New repository
2. Name: `xai-blockchain`
3. Public repository
4. Don't initialize with README
5. Create repository

## Step 5: Push

```bash
git remote add origin https://github.com/YOUR_USERNAME/xai-blockchain.git
git push -u origin main
```

Use Personal Access Token as password (not your GitHub password).

## Security

- **NEVER** access without Tor
- **NEVER** commit with personal git config
- **ALWAYS** verify `git log` shows anonymous identity

## Verify

```bash
git log --pretty=format:"%an <%ae>" | sort -u
```

Should show only: `XAI Developer <noreply@protonmail.com>`
