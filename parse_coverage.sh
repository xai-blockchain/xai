#!/bin/bash
# Extract totals from coverage.json using basic text processing
if [ ! -f coverage.json ]; then
    echo "coverage.json not found"
    exit 1
fi

# Use grep and sed to find the totals section
# The totals section is at the very end of the JSON before the final }
totals_line=$(grep -o '"totals":{[^}]*"percent_covered":[^,}]*' coverage.json | head -1)

# Extract the percent_covered value
percent=$(echo "$totals_line" | grep -o '"percent_covered":[0-9.]*' | grep -o '[0-9.]*')

# Also try to extract covered_lines and num_statements  
covered=$(grep -o '"totals":{[^}]*"covered_lines":[0-9]*' coverage.json | head -1 | grep -o '[0-9]*$')
total=$(grep -o '"totals":{[^}]*"num_statements":[0-9]*' coverage.json | head -1 | grep -o '[0-9]*$')

echo "Overall Coverage: ${percent}%"
echo "Covered: ${covered} / ${total}"
