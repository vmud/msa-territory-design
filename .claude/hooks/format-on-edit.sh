#!/bin/bash
# PostToolUse hook: Auto-format Python files after edit
# Runs black and isort silently to maintain code consistency

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Only process Python files that exist
if [[ "$file_path" == *.py ]] && [[ -f "$file_path" ]]; then
    # Run black and isort silently
    # Use --quiet to suppress output unless there's an error
    black --quiet "$file_path" 2>/dev/null
    isort --quiet "$file_path" 2>/dev/null
fi

exit 0
