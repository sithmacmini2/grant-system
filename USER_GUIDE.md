# Grant Intelligence Workflow System - User Guide

## Overview

The Grant Intelligence Workflow System automates grant research for The MUSE Foundation of Rhode Island, generating 4 parallel outputs from a single research pass: grant briefs, proposal drafts, comparative rankings, and tracking dashboards.

## Quick Start

### Running Research

```bash
# Full monthly research (Layers 1-4)
python3 /home/sithmm2_admin/grants-system/hermes-tasks/monthly-research.py

# Ad-hoc research by keyword
python3 /home/sithmm2_admin/grants-system/hermes-tasks/adhoc-research.py "youth"
```

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/grants-this-month` | View current tracking dashboard |
| `/grant-brief [name]` | Get specific grant brief |
| `/rank-by-deadline` | Sort matrix by urgency |
| `/funder-intel [name]` | Get funder profile |
| `/pattern-scan` | View success patterns (6 months) |
| `/research [keywords]` | Trigger subset research |
| `/deadline-alerts` | Show urgent grants (<14 days) |
| `/status` | System status |

### Viewing Outputs

All outputs are stored in:
- **Briefs**: `/home/sithmm2_admin/grants-system/outputs/briefs/[YYYY-MM]/`
- **Proposals**: `/home/sithmm2_admin/grants-system/outputs/proposals/[YYYY-MM]/`
- **Matrix**: `/home/sithmm2_admin/grants-system/outputs/matrix/[YYYY-MM]/`
- **Dashboard**: `/home/sithmm2_admin/grants-system/outputs/tracking/[YYYY-MM]/`

### Scheduled Tasks

| Task | Schedule |
|------|----------|
| Weekly Deadline Check | Every Monday 9am |
| Monthly Research | 1st Friday 9am |
| Quarterly Patterns | Jan 1, Apr 1, Jul 1, Oct 1 |

## Understanding Fit Scores

- **8-10**: Strong match - prioritize for full application
- **6-7**: Good match - start draft
- **4-5**: Monitor - track only
- **1-3**: Weak match - skip

## Updating Outcomes

When a grant outcome is known:
1. Move brief to `/wiki/Grants/2026/05-Archive/Won/` or `Lost/`
2. System will use this for future pattern matching

## Support

For issues or questions, check:
- Logs: `/home/sithmm2_admin/grants-system/logs/`
- Documentation: `/home/sithmm2_admin/grants-system/docs/`

---
*Last updated: 2026-04-17*