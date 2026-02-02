#!/bin/bash
# PostToolUse hook: Validate YAML syntax on edit
# Exit 0 always (non-blocking), output warnings to stderr

# Read hook input from stdin
input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Only validate YAML files
if [[ "$file_path" == *.yaml ]] || [[ "$file_path" == *.yml ]]; then
    # Check if file exists
    if [[ -f "$file_path" ]]; then
        # Run Python YAML validation, capture output
        error=$(python3 -c "
import yaml
import sys
try:
    with open('$file_path') as f:
        yaml.safe_load(f)
except yaml.YAMLError as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
" 2>&1)
        yaml_exit=$?

        if [[ $yaml_exit -ne 0 ]] && [[ -n "$error" ]]; then
            # Escape newlines and quotes for JSON
            escaped_error=$(echo "$error" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' ' ')
            echo "{\"systemMessage\": \"⚠️ YAML syntax error in $file_path: $escaped_error\"}"
        fi
    fi
fi

# Always exit 0 - this is a non-blocking warning hook
exit 0
