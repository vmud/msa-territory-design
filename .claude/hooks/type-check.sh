#!/bin/bash
# PostToolUse hook: Run mypy on edited Python files
# Reports type hints issues as system messages

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Only process Python files that exist
if [[ "$file_path" == *.py ]] && [[ -f "$file_path" ]]; then
    # Run mypy and capture output (excluding success message)
    type_output=$(mypy --no-error-summary "$file_path" 2>&1 | grep -v "Success" | head -5)

    if [[ -n "$type_output" ]]; then
        # Escape for JSON and report as system message
        escaped_output=$(echo "$type_output" | tr '\n' ' ' | sed 's/"/\\"/g')
        echo "{\"systemMessage\": \"Type hints: $escaped_output\"}"
    fi
fi

exit 0
