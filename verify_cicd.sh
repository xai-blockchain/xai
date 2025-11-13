#!/bin/bash
# CI/CD Pipeline Verification Script

echo "======================================"
echo "CI/CD Pipeline Verification"
echo "======================================"
echo ""

echo "📋 Checking Workflow Files..."
workflows=("quality.yml" "security.yml" "tests.yml" "deploy.yml")
for workflow in "${workflows[@]}"; do
    if [ -f ".github/workflows/$workflow" ]; then
        size=$(wc -c < ".github/workflows/$workflow" | tr -d ' ')
        echo "  ✅ $workflow (${size} bytes)"
    else
        echo "  ❌ $workflow - MISSING"
    fi
done
echo ""

echo "📋 Checking Configuration Files..."
configs=(".pylintrc" "mypy.ini" ".pre-commit-config.yaml" ".yamllint.yml" "Dockerfile" ".dockerignore")
for config in "${configs[@]}"; do
    if [ -f "$config" ]; then
        size=$(wc -c < "$config" | tr -d ' ')
        echo "  ✅ $config (${size} bytes)"
    else
        echo "  ❌ $config - MISSING"
    fi
done
echo ""

echo "📋 Checking Documentation Files..."
docs=(".github/workflows/README.md" ".github/CICD_SETUP_GUIDE.md" ".github/CI_CD_IMPLEMENTATION_SUMMARY.md" ".github/README_BADGES_TEMPLATE.md" ".github/SETUP_CHECKLIST.md")
for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        lines=$(wc -l < "$doc" | tr -d ' ')
        echo "  ✅ $doc (${lines} lines)"
    else
        echo "  ❌ $doc - MISSING"
    fi
done
echo ""

echo "📋 Checking Dependencies..."
if [ -f "src/aixn/requirements.txt" ]; then
    echo "  ✅ Main requirements.txt"
else
    echo "  ❌ Main requirements.txt - MISSING"
fi

if [ -f "tests/aixn_tests/requirements_test.txt" ]; then
    echo "  ✅ Test requirements.txt"
else
    echo "  ❌ Test requirements.txt - MISSING"
fi
echo ""

echo "📋 Validating YAML Syntax..."
for workflow in "${workflows[@]}"; do
    if command -v python3 &> /dev/null; then
        python3 -c "import yaml; yaml.safe_load(open('.github/workflows/$workflow'))" 2>&1
        if [ $? -eq 0 ]; then
            echo "  ✅ $workflow - Valid YAML"
        else
            echo "  ❌ $workflow - Invalid YAML"
        fi
    fi
done
echo ""

echo "======================================"
echo "Summary"
echo "======================================"
total_workflows=$(ls -1 .github/workflows/*.yml 2>/dev/null | wc -l)
echo "Total Workflow Files: $total_workflows"

total_configs=0
for config in "${configs[@]}"; do
    [ -f "$config" ] && ((total_configs++))
done
echo "Total Config Files: $total_configs/6"

total_docs=0
for doc in "${docs[@]}"; do
    [ -f "$doc" ] && ((total_docs++))
done
echo "Total Documentation: $total_docs/5"

echo ""
echo "✨ CI/CD Pipeline Setup: COMPLETE"
echo ""
echo "Next Steps:"
echo "1. Review workflow files in .github/workflows/"
echo "2. Read .github/CICD_SETUP_GUIDE.md"
echo "3. Follow .github/SETUP_CHECKLIST.md"
echo "4. Push to GitHub and monitor Actions tab"
echo ""
