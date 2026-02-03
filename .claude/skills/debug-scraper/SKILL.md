---
name: debug-scraper
description: Debug failing scraper with systematic checks
---

# Debug Scraper

Systematic debugging for scraper failures.

## Required Args
- retailer: The retailer to debug (e.g., "verizon", "target")

## Workflow

### 1. Check Recent Logs

```bash
# Find the most recent log file
tail -100 logs/$(ls -t logs/*.log 2>/dev/null | head -1) 2>/dev/null || echo "No logs found"
```

### 2. Test Scraper with Limited Run

```bash
python run.py --retailer {retailer} --test --limit 3
```

### 3. Compare with Previous Run

Use the `/compare-runs` skill to see what changed between runs:
```bash
# Check if previous output exists
ls -la data/{retailer}/output/
```

### 4. Check Checkpoint State

```bash
ls -la data/{retailer}/checkpoints/
```

If checkpoints exist, you can resume:
```bash
python run.py --retailer {retailer} --resume
```

### 5. Validate Store Data

```python
from src.shared.utils import validate_stores_batch
import json

with open(f'data/{retailer}/output/stores_latest.json') as f:
    stores = json.load(f)

summary = validate_stores_batch(stores)
print(f"Valid: {summary['valid_count']}/{summary['total_count']}")
print(f"Issues: {summary['issues']}")
```

### 6. Check Proxy Status (if applicable)

```bash
# Test proxy connectivity
python run.py --retailer {retailer} --proxy residential --validate-proxy --test --limit 1
```

### 7. Check Retailer Configuration

```bash
# View retailer config
grep -A 30 "^  {retailer}:" config/retailers.yaml
```

## Common Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| 429 errors | Rate limiting | Increase delays in retailers.yaml |
| Empty stores | Site changed | Check sitemap/API endpoint |
| Timeout errors | Network/proxy | Check proxy status, increase timeout |
| Parse errors | HTML changed | Update selectors in scraper |
| Missing fields | Schema change | Update field extraction logic |

## Quick Commands Reference

```bash
# Full status check
python run.py --status

# Clear checkpoints and retry
rm -rf data/{retailer}/checkpoints/*
python run.py --retailer {retailer}

# Run with verbose logging
python run.py --retailer {retailer} --test 2>&1 | tee debug.log
```
