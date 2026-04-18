# Grant Intelligence Workflow System - Implementation Plan

## Organization Profile
- **Name**: The MUSE Foundation of Rhode Island
- **Type**: 501(c)(3) nonprofit, Providence, RI
- **Mission**: "Enrich. Empower. Equip."
- **Focus Areas**: Black/Brown community advancement, youth leadership, philanthropy education, advocacy, community-led initiatives
- **Key Programs**: RI Black Philanthropy Month, YESpvd! youth programming, Juneteenth advocacy, MSVL Bridge Concert Series, BLKGivin' micro-grants

## Environment Paths
| Component | Path |
|-----------|------|
| System root | `/home/sithmm2_admin/grants-system/` |
| Obsidian vault | `/home/sithmm2_admin/wiki/` |
| Opencode | `/home/sithmm2_admin/.opencode/bin/opencode` |
| Hermes | `/home/sithmm2_admin/.local/bin/hermes` |
| Telegram bot token | `TELEGRAM_BOT_TOKEN` environment variable |
| Test data | `/home/sithmm2_admin/Downloads/Downloaded-Grants/` |

## 5-Layer Architecture

### Layer 1: Data Ingestion (Opencode)
- 10 scrapers for: grants.gov, foundationcenter.org, candid.org, compasspoint.org, ri.gov/grants, mass.gov/grants, connecticut.gov/grants, urban.org, ncrp.org, councilonfoundations.org
- Output: JSON with grant_id, name, funder, deadline, amount, criteria, url, source_db, scraped_date

### Layer 2: Normalization & Enrichment (Hermes)
- Fuzzy match funder names to LLM Wiki profiles
- Extract eligibility criteria
- Standardize deadlines (days_remaining, urgency_level)
- Flag known_rejections, past_success

### Layer 3: Intelligence Scanning (Cerebro-Skill)
- Pattern extraction from past wins
- Funder clustering
- Gap analysis
- Compound opportunities
- Red flag detection

### Layer 4: Synthesis & Output Generation
- Output 1: Grant Briefs
- Output 2: Proposal Drafts
- Output 3: Comparative Matrix
- Output 4: Tracking Dashboard

### Layer 5: Storage & Memory Loops
- Obsidian storage with GitHub sync
- LLM Wiki auto-updates

## Telegram Commands
- /grants or /grants_this_month - Current tracking dashboard
- /brief or /grant_brief [name] - Specific brief
- /rank or /rank_by_deadline - Matrix sorted by urgency
- /funder_intel [name] - Funder profile
- /patterns or /pattern_scan - Cerebro themes
- /research [keywords] - Search current grant data
- /alerts or /deadline_alerts - Grants due < 14 days
- /status - System status

## Implementation Phases
1. Foundation (Week 1): Directory structure, configs, test data
2. Data Processing (Week 2): Enrichment pipeline
3. Intelligence (Week 3): Cerebro integration, output generators
4. Automation (Week 4): Scheduled tasks, Telegram handlers
5. Deployment (Week 5): Test & validate

---
*Created: 2026-04-17*
*Owner: J'Juan Wilson Jr.*
