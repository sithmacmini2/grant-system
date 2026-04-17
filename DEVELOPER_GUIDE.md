# Grant Intelligence Workflow System - Developer Guide

## Architecture

```
Layer 1: Opencode Scrapers → Layer 2: Enrichment → Layer 3: Cerebro → Layer 4: Outputs → Layer 5: Storage
```

## Scripts Overview

| Script | Layer | Purpose |
|--------|-------|---------|
| `generate_test_data.py` | - | Generate synthetic test grants |
| `enrich-grants.py` | 2 | Normalize + enrich grants |
| `cerebro-integration.py` | 3 | Intelligence scan & fit scoring |
| `brief-generator.py` | 4a | Generate grant briefs |
| `proposal-generator.py` | 4b | Generate proposal drafts |
| `matrix-generator.py` | 4c | Generate comparative matrix |
| `dashboard-generator.py` | 4d | Generate tracking dashboard |
| `monthly-research.py` | 5 | Orchestrate full cycle |
| `weekly-deadline-check.py` | 5 | Check deadlines |
| `quarterly-patterns.py` | 5 | Quarterly analysis |
| `adhoc-research.py` | 5 | Keyword-filtered research |

## Configuration Files

- `configs/system-config.json` - Main system config
- `configs/grant-databases.json` - Scraper configurations
- `configs/grant_normalized.schema.json` - Data schema
- `configs/logging.yaml` - Logging config

## Adding New Scrapers

Edit `configs/grant-databases.json`:
```json
{
  "id": "new-source",
  "name": "New Source",
  "type": "federal|foundation|state",
  "base_url": "https://...",
  "fields": {...}
}
```

## Modifying Fit Scoring

Edit `cerebro-integration.py` - function `calculate_fit_score()`:
- Adjust weights for focus alignment, eligibility, amount, timeline, history

## Modifying Templates

- Brief template: `brief-generator.py` - `generate_brief()`
- Proposal template: `proposal-generator.py` - `generate_proposal()`
- Dashboard template: `dashboard-generator.py` - `generate_dashboard()`

## Testing

```bash
# Run test data generation
python3 hermes-tasks/generate_test_data.py

# Run enrichment
python3 hermes-tasks/enrich-grants.py 2026-04

# Run full pipeline
python3 hermes-tasks/monthly-research.py
```

## Data Paths

- Raw data: `data/raw/[YYYY-MM]/`
- Enriched: `data/enriched/[YYYY-MM]/`
- Intelligence: `data/intelligence/[YYYY-MM]/`
- Outputs: `outputs/[type]/[YYYY-MM]/`

---
*Last updated: 2026-04-17*