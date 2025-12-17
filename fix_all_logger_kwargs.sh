#!/bin/bash
#
# Fix all logger calls with error_type= kwargs to use extra dict
#

cd /home/hudson/blockchain-projects/xai

# Find all files with error_type= that still need fixing
files=$(grep -rl "error_type=" src/xai/ --include="*.py" | grep -v "__pycache__")

count=0
for file in $files; do
    # Check if file still has the old pattern (not using extra={)
    if grep -q 'error_type=' "$file" && ! grep -B2 "error_type=" "$file" | grep -q "extra={"; then
        echo "Checking $file..."
        # This file might still have issues, let's check manually
        if grep -A1 -B1 'logger\.\(debug\|info\|warning\|error\|critical\)(' "$file" | grep -q 'error_type=.*"'; then
            echo "  -> Still has direct error_type kwarg"
            ((count++))
        fi
    fi
done

echo ""
echo "Found $count files that may still need fixing"
echo ""
echo "These need manual review and fixing using the Edit tool"
