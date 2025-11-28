# DEFECT-003: pyproject.toml Package Configuration Error

**Severity:** P0 - Critical
**Status:** Fixed - Instance refresh in progress
**Discovered:** 2025-11-22 02:40 UTC
**Fixed:** 2025-11-22 02:41 UTC

## Problem
```toml
# WRONG:
[tool.setuptools]
packages = ["src.xai"]  # ❌
```

This caused `pip install -e .` to fail or misconfigure the package, preventing the blockchain application from starting on port 5000.

## Fix
```toml
# CORRECT:
[tool.setuptools]
packages = ["xai"]  # ✅
```

## Actions Taken
1. Fixed pyproject.toml line 256
2. Repackaged: `xai-blockchain-v3.tar.gz`
3. Uploaded to S3 (overwrote v1.0.0)
4. Instance refresh: `116aa2bc-e090-45cd-bfcd-735080cf619e`

## Verification
- Wait for refresh completion (~20-25 min)
- Check instances become healthy
- Test API endpoints

**File:** `C:\Users\decri\GitClones\Crypto\pyproject.toml:256`
