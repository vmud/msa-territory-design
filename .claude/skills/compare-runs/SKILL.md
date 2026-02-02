---
name: compare-runs
description: Compare current vs previous scraper run to see store changes
disable-model-invocation: true
---

# Compare Scraper Runs

Shows what changed between current and previous scraper runs using the ChangeDetector.

## Usage

| Command | Description |
|---------|-------------|
| `/compare-runs verizon` | Compare Verizon runs |
| `/compare-runs all` | Compare all retailers |
| `/compare-runs target --details` | Show full details of changed stores |

## What Gets Compared

The ChangeDetector identifies:

### New Stores (+)
Stores present in current run but not in previous run. Identifies by:
- `store_id` (primary identifier)
- `url` (fallback, especially for Best Buy)
- Address-based key (name + street_address + city + state + zip + phone)

### Closed Stores (-)
Stores present in previous run but missing from current run.

### Modified Stores (~)
Stores present in both runs with changes to:
- `country`, `latitude`, `longitude`
- `store_type`, `status`

### Unchanged Stores (=)
Stores identical between runs.

## Data Files

The comparison uses:
- `data/{retailer}/output/stores_latest.json` - Current run
- `data/{retailer}/output/stores_previous.json` - Previous run
- `data/{retailer}/fingerprints.json` - Cached fingerprints for faster comparison

## Execution Steps

1. Load current and previous store data
2. Run `ChangeDetector.detect_changes()`
3. Generate summary report with:
   - Store counts (previous vs current)
   - Change breakdown (+new, -closed, ~modified, =unchanged)
   - Sample of new/closed stores (first 5)
   - Types of modifications seen

## Example Output

```
=== Change Report: verizon ===
Comparing: 2025-01-25 run → 2025-01-26 run

Store Counts:
  Previous: 1,245
  Current:  1,247
  Delta:    +2

Changes:
  + 5 new stores
  - 3 closed stores
  ~ 12 modified stores
  = 1,227 unchanged

New Stores (showing 5):
  - VZW-9876: "Verizon - Downtown Seattle" (123 Pike St, Seattle, WA)
  - VZW-9877: "Verizon - Bellevue Square" (456 Bellevue Way, Bellevue, WA)
  ... 3 more

Closed Stores (showing 3):
  - VZW-1111: "Verizon - Old Mall Location" (789 Mall Rd, Portland, OR)
  ... 2 more

Modifications:
  - 8 stores: coordinates updated
  - 4 stores: status changed
```

## Implementation

```python
from src.change_detector import ChangeDetector

detector = ChangeDetector(retailer="verizon")
report = detector.detect_changes()

print(f"Previous: {report.total_previous}")
print(f"Current: {report.total_current}")
print(report.summary())

if report.new_stores:
    print(f"\nNew stores ({len(report.new_stores)}):")
    for store in report.new_stores[:5]:
        print(f"  - {store.get('store_id')}: {store.get('name')}")
```

## Error Handling

- If no `stores_previous.json` exists, report "First run - no comparison available"
- If no `stores_latest.json` exists, suggest running the scraper first
- If retailer doesn't exist, list available retailers

## Related Commands

- `/validate-output {retailer}` - Check data quality of current run
- `/run-scraper {retailer} --incremental` - Run scraper in incremental mode
