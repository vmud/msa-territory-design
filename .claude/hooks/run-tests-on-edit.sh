#!/bin/bash
# PostToolUse hook: Run pytest after editing Python files
# Runs quick tests silently to catch regressions early

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Only run tests for Python files
if [[ "$file_path" == *.py ]] && [[ -f "$file_path" ]]; then
    # Run pytest quietly, suppress output unless there are failures
    test_output=$(python -m pytest --tb=short -q 2>&1)
    exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        # Only report if tests failed
        failed_count=$(echo "$test_output" | grep -oE '[0-9]+ failed' | head -1)
        if [[ -n "$failed_count" ]]; then
            echo "{\"systemMessage\": \"Tests: $failed_count\"}"
        fi
    fi
fi

exit 0
