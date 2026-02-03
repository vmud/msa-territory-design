---
name: scraper-status
description: Get status of all scrapers for context
user-invocable: false
---

# Scraper Status

Quick status check for all retailers. Use this skill to understand the current state of scrapers before answering questions.

## Check Commands

### Overall Status

```bash
python run.py --status
```

### Recent Run Results

```bash
# List latest output files with timestamps
ls -la data/*/output/stores_latest.json 2>/dev/null | awk '{print $6, $7, $8, $9}'
```

### Store Counts by Retailer

```bash
for dir in data/*/output; do
  retailer=$(basename $(dirname $dir))
  if [ -f "$dir/stores_latest.json" ]; then
    count=$(python3 -c "import json; print(len(json.load(open('$dir/stores_latest.json'))))" 2>/dev/null)
    echo "$retailer: $count stores"
  fi
done
```

### Check for Recent Errors

```bash
# Find log files with errors from last 24 hours
find logs -name "*.log" -mtime -1 -exec grep -l -E "error|failed|exception" {} \; 2>/dev/null
```

### Checkpoint Status

```bash
# Show which retailers have active checkpoints
for dir in data/*/checkpoints; do
  retailer=$(basename $(dirname $dir))
  if [ -d "$dir" ] && [ "$(ls -A $dir 2>/dev/null)" ]; then
    echo "$retailer: Has checkpoints (can resume)"
  fi
done
```

### Enabled Retailers

```bash
# List enabled retailers from config
grep -B1 "enabled:" config/retailers.yaml | grep -E "^  [a-z]+:" | sed 's/://g' | awk '{print $1}'
```

## Output Summary

When reporting status, include:
- Number of enabled retailers
- Last successful run times per retailer
- Any recent errors or warnings
- Checkpoint status (resumable runs)
- Total store counts
