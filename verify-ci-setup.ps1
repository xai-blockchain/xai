# CI/CD Setup Verification Script for Crypto Project
# Run this to verify your CI/CD pipeline is properly configured

Write-Host "🔍 Verifying CI/CD Setup for Crypto Project..." -ForegroundColor Cyan
Write-Host ""

$errors = 0
$warnings = 0

# Check if workflow file exists
Write-Host "✓ Checking workflow file..." -ForegroundColor Yellow
if (Test-Path ".github/workflows/comprehensive-ci.yml") {
    Write-Host "  ✅ comprehensive-ci.yml exists" -ForegroundColor Green
} else {
    Write-Host "  ❌ comprehensive-ci.yml not found!" -ForegroundColor Red
    $errors++
}

# Check if this is a git repository
Write-Host "`n✓ Checking git repository..." -ForegroundColor Yellow
if (Test-Path ".git") {
    Write-Host "  ✅ Git repository detected" -ForegroundColor Green

    # Check if remote is configured
    $remote = git remote get-url origin 2>$null
    if ($remote) {
        Write-Host "  ✅ Remote origin: $remote" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  No remote origin configured" -ForegroundColor Yellow
        $warnings++
    }
} else {
    Write-Host "  ❌ Not a git repository!" -ForegroundColor Red
    $errors++
}

# Check Python installation
Write-Host "`n✓ Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.(1[0-2]|[0-9])") {
        Write-Host "  ✅ Python installed: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Python version may not be optimal: $pythonVersion" -ForegroundColor Yellow
        Write-Host "     Recommended: Python 3.10+" -ForegroundColor Yellow
        $warnings++
    }
} catch {
    Write-Host "  ❌ Python not found!" -ForegroundColor Red
    $errors++
}

# Check if requirements files exist
Write-Host "`n✓ Checking dependency files..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    Write-Host "  ✅ requirements.txt exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  requirements.txt not found" -ForegroundColor Yellow
    $warnings++
}

if (Test-Path "requirements-dev.txt") {
    Write-Host "  ✅ requirements-dev.txt exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  requirements-dev.txt not found" -ForegroundColor Yellow
    $warnings++
}

# Check if tests directory exists
Write-Host "`n✓ Checking test structure..." -ForegroundColor Yellow
if (Test-Path "tests") {
    Write-Host "  ✅ tests/ directory exists" -ForegroundColor Green
    $testCount = (Get-ChildItem -Path "tests" -Filter "*test*.py" -Recurse).Count
    Write-Host "  ℹ️  Found $testCount test files" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠️  tests/ directory not found" -ForegroundColor Yellow
    $warnings++
}

# Check if source directory exists
Write-Host "`n✓ Checking source structure..." -ForegroundColor Yellow
if (Test-Path "src") {
    Write-Host "  ✅ src/ directory exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  src/ directory not found" -ForegroundColor Yellow
    $warnings++
}

# Check for pytest configuration
Write-Host "`n✓ Checking pytest configuration..." -ForegroundColor Yellow
if (Test-Path "pytest.ini" -or Test-Path "pyproject.toml") {
    Write-Host "  ✅ pytest configuration found" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  No pytest configuration found" -ForegroundColor Yellow
    $warnings++
}

# Check GitHub Actions status (if connected to internet)
Write-Host "`n✓ Checking GitHub Actions status..." -ForegroundColor Yellow
if ($remote -and $remote -match "github.com[:/](.+?)(?:\.git)?$") {
    $repo = $matches[1]
    Write-Host "  ℹ️  Repository: $repo" -ForegroundColor Cyan
    Write-Host "  🔗 GitHub Actions: https://github.com/$repo/actions" -ForegroundColor Cyan
    Write-Host "  ℹ️  Visit the URL above to check pipeline status" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠️  Unable to determine GitHub repository" -ForegroundColor Yellow
    $warnings++
}

# Summary
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "📊 VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

if ($errors -eq 0 -and $warnings -eq 0) {
    Write-Host "✅ Perfect! Your CI/CD setup looks great!" -ForegroundColor Green
} elseif ($errors -eq 0) {
    Write-Host "⚠️  Setup is functional but has $warnings warning(s)" -ForegroundColor Yellow
} else {
    Write-Host "❌ Found $errors error(s) and $warnings warning(s)" -ForegroundColor Red
}

Write-Host "`n📚 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Check GitHub Actions: https://github.com/$repo/actions" -ForegroundColor White
Write-Host "  2. Add Codecov token (optional): See CI_CD_SETUP_GUIDE.md" -ForegroundColor White
Write-Host "  3. Add SonarQube token (optional): See CI_CD_SETUP_GUIDE.md" -ForegroundColor White
Write-Host "  4. Review the comprehensive guide: CI_CD_SETUP_GUIDE.md" -ForegroundColor White

Write-Host "`n✨ Done!" -ForegroundColor Green
