---
name: validate-output
description: Run data quality validation on scraped store data
disable-model-invocation: true
---

# Validate Scraper Output

Validates scraped store data for quality issues using the project's validation utilities.

## Usage

| Command | Description |
|---------|-------------|
| `/validate-output verizon` | Validate Verizon store data |
| `/validate-output all` | Validate all retailers |
| `/validate-output target --strict` | Strict mode (treat warnings as errors) |

## What Gets Validated

### Required Fields (errors if missing)
- `store_id` - Unique store identifier
- `name` - Store name
- `street_address` - Street address
- `city` - City name
- `state` - State code (2 letters for US)

### Recommended Fields (warnings if missing)
- `latitude` / `longitude` - Geographic coordinates
- `phone` - Contact phone number
- `url` - Store page URL

### Additional Checks
- Coordinates within valid bounds (-90 to 90 lat, -180 to 180 lon)
- Not (0,0) coordinates (common scraping error)
- Duplicate store_id detection
- Empty string vs null field values

## Execution Steps

1. Load store data from `data/{retailer}/output/stores_latest.json`
2. Run `validate_stores_batch()` from `src/shared/utils.py`
3. Generate quality report with:
   - Total stores and valid count
   - Field completeness percentages
   - List of specific errors/warnings (first 10)
   - Critical issues requiring attention

## Example Output

```
=== Validation Report: verizon ===
Total stores: 1,247
Valid stores: 1,189 (95.3%)

Field Completeness:
  store_id:       100.0%
  name:           100.0%
  street_address: 100.0%
  city:           100.0%
  state:          100.0%
  latitude:        98.2%
  longitude:       98.2%
  phone:           87.4%

Issues Found:
  - ERROR: Store 'VZW-1234' missing latitude/longitude
  - WARNING: Store 'VZW-5678' has coordinates (0.0, 0.0)
  ... (22 more issues)
```

## Implementation

```python
import json
from pathlib import Path
from src.shared.utils import validate_stores_batch

# Load data
data_path = Path(f"data/{retailer}/output/stores_latest.json")
with open(data_path) as f:
    stores = json.load(f)

# Validate
summary = validate_stores_batch(stores, strict=strict_mode, log_issues=True)

# Report completeness
fields = ['store_id', 'name', 'street_address', 'city', 'state', 'latitude', 'longitude', 'phone', 'url']
for field in fields:
    present = sum(1 for s in stores if s.get(field))
    pct = (present / len(stores)) * 100
    print(f"  {field}: {pct:.1f}%")
```

## Error Handling

- If no `stores_latest.json` exists, suggest running the scraper first
- If file is empty or malformed, report JSON parse error
- If retailer doesn't exist, list available retailers
