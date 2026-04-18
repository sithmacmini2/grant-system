#!/usr/bin/env python3
"""
Tracking Dashboard - Graphical UI Generator
Creates an interactive HTML dashboard from grant data
"""

import json
from datetime import datetime
from collections import defaultdict

from grants_context import active_month, grants_path, wiki_path

GRANTS_ROOT = grants_path()
WIKI_ROOT = wiki_path()


def load_grants():
    """Load enriched grants"""
    f = GRANTS_ROOT / "data" / "enriched" / active_month() / "grants-enriched.json"
    if f.exists():
        with f.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    return []


def generate_tracking_ui():
    """Generate HTML tracking dashboard"""
    grants = load_grants()

    if not grants:
        print("No grant data. Run run-all.py first.")
        return

    urgent = sorted(
        [g for g in grants if g.get("enrichment", {}).get("urgency_level") == "HIGH"],
        key=lambda g: g.get("enrichment", {}).get("days_remaining", 999),
    )

    all_grants = sorted(
        grants, key=lambda g: g.get("enrichment", {}).get("days_remaining", 999)
    )

    by_status = defaultdict(list)
    for g in grants:
        status = g.get("status", "new")
        by_status[status].append(g)

    stats = {
        "total": len(grants),
        "high_fit": len(
            [g for g in grants if g.get("intelligence", {}).get("fit_score", 0) >= 7]
        ),
        "proposals": len(
            [g for g in grants if g.get("intelligence", {}).get("fit_score", 0) >= 6]
        ),
        "urgent": len(urgent),
        "total_amount": sum(g.get("amount", 0) for g in grants),
    }

    urgency_rows = ""
    for g in urgent[:10]:
        days = g.get("enrichment", {}).get("days_remaining", 0)
        fit = g.get("intelligence", {}).get("fit_score", 0)
        rec = g.get("intelligence", {}).get("recommendation", "")
        deadline = g.get("deadline", "")

        color = "#ef4444" if days <= 7 else "#f59e0b"
        fit_color = "#22c55e" if fit >= 7 else "#fbbf24" if fit >= 5 else "#ef4444"

        urgency_rows += f"""
        <div class="grant-card urgent" style="border-left: 4px solid {color};">
            <div class="grant-header">
                <span class="grant-name">{g.get("name", "")[:45]}</span>
                <span class="days-badge" style="background:{color};">{days} days</span>
            </div>
            <div class="grant-details">
                <span class="funder">{g.get("funder", "")}</span>
                <span class="amount">${g.get("amount", 0):,}</span>
                <span class="deadline">{deadline}</span>
            </div>
            <div class="grant-meta">
                <span class="fit-score" style="color:{fit_color};">Fit: {fit}/10</span>
                <span class="recommendation">{rec}</span>
            </div>
        </div>"""

    if not urgency_rows:
        urgency_rows = "<p style='padding:20px;color:#666;'>No urgent deadlines!</p>"

    all_rows = ""
    for g in all_grants[:20]:
        days = g.get("enrichment", {}).get("days_remaining", 0)
        fit = g.get("intelligence", {}).get("fit_score", 0)
        rec = g.get("intelligence", {}).get("recommendation", "")
        deadline = g.get("deadline", "")

        fit_color = "#22c55e" if fit >= 7 else "#fbbf24" if fit >= 5 else "#ef4444"

        all_rows += f"""
        <div class="grant-card">
            <div class="grant-header">
                <span class="grant-name">{g.get("name", "")[:45]}</span>
                <span class="days-badge" style="background:#374151;">{days}d</span>
            </div>
            <div class="grant-details">
                <span class="funder">{g.get("funder", "")[:25]}</span>
                <span class="amount">${g.get("amount", 0):,}</span>
                <span class="deadline">{deadline}</span>
            </div>
            <div class="grant-meta">
                <span class="fit-score" style="color:{fit_color};">Fit: {fit}/10</span>
                <span class="recommendation">{rec}</span>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grant Tracking Dashboard - MUSE Foundation</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: linear-gradient(135deg, #1e3a5f 0%, #0f2027 100%); min-height: 100vh; color: #fff; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        
        .header {{ text-align: center; padding: 30px 0; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }}
        .header p {{ color: #94a3b8; font-size: 1.1rem; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-box {{ background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 16px; padding: 25px; text-align: center; border: 1px solid rgba(255,255,255,0.1); transition: transform 0.3s; }}
        .stat-box:hover {{ transform: translateY(-5px); }}
        .stat-number {{ font-size: 2.5rem; font-weight: bold; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stat-label {{ color: #94a3b8; margin-top: 5px; font-size: 0.9rem; }}
        
        .section {{ background: rgba(255,255,255,0.05); border-radius: 20px; padding: 25px; margin-bottom: 25px; backdrop-filter: blur(10px); }}
        .section h2 {{ color: #e2e8f0; margin-bottom: 20px; font-size: 1.4rem; display: flex; align-items: center; gap: 10px; }}
        .section h2 .icon {{ font-size: 1.5rem; }}
        
        .grant-card {{ background: rgba(255,255,255,0.08); border-radius: 12px; padding: 18px; margin-bottom: 12px; transition: all 0.3s; }}
        .grant-card:hover {{ background: rgba(255,255,255,0.12); transform: translateX(5px); }}
        
        .grant-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .grant-name {{ font-weight: 600; font-size: 1rem; }}
        .days-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }}
        
        .grant-details {{ display: flex; gap: 20px; color: #94a3b8; font-size: 0.9rem; margin-bottom: 10px; }}
        .grant-meta {{ display: flex; justify-content: space-between; font-size: 0.85rem; }}
        .fit-score {{ font-weight: 600; }}
        .recommendation {{ color: #94a3b8; }}
        
        .timeline {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px; }}
        .timeline-item {{ padding: 8px 16px; background: rgba(255,255,255,0.1); border-radius: 20px; font-size: 0.85rem; }}
        
        .refresh-btn {{ display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; }}
        .refresh-btn:hover {{ transform: scale(1.05); box-shadow: 0 10px 30px rgba(102,126,234,0.4); }}
        
        .action-bar {{ text-align: center; margin: 30px 0; }}
        
        .legend {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #94a3b8; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 3px; }}
        
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }}
        @media (max-width: 900px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
        
        .footer {{ text-align: center; color: #64748b; padding: 20px; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Grant Tracking Dashboard</h1>
            <p>The MUSE Foundation of Rhode Island</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{stats["total"]}</div>
                <div class="stat-label">Total Grants</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{stats["high_fit"]}</div>
                <div class="stat-label">High Priority (7+)</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{stats["proposals"]}</div>
                <div class="stat-label">Proposals Ready</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{stats["urgent"]}</div>
                <div class="stat-label">Urgent Deadlines</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">${stats["total_amount"] / 1000:.0f}k</div>
                <div class="stat-label">Total Available</div>
            </div>
        </div>
        
        <div class="action-bar">
            <a href="#" onclick="location.reload()" class="refresh-btn">🔄 Refresh Data</a>
        </div>
        
        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background:#ef4444;"></div> ≤7 days</div>
            <div class="legend-item"><div class="legend-color" style="background:#f59e0b;"></div> 8-14 days</div>
            <div class="legend-item"><div class="legend-color" style="background:#22c55e;"></div> Fit 7+</div>
            <div class="legend-item"><div class="legend-color" style="background:#fbbf24;"></div> Fit 5-6</div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <h2><span class="icon">⚠️</span> Urgent Deadlines (≤14 days)</h2>
                {urgency_rows}
            </div>
            
            <div class="section">
                <h2><span class="icon">📋</span> All Grants (by deadline)</h2>
                {all_rows}
            </div>
        </div>
        
        <div class="section">
            <h2><span class="icon">🗓️</span> Timeline View</h2>
            <div class="timeline">
                <div class="timeline-item">This Week: {len([g for g in all_grants if g.get("enrichment", {}).get("days_remaining", 0) <= 7])} grants</div>
                <div class="timeline-item">This Month: {len([g for g in all_grants if g.get("enrichment", {}).get("days_remaining", 0) <= 30])} grants</div>
                <div class="timeline-item">Next 60 days: {len([g for g in all_grants if g.get("enrichment", {}).get("days_remaining", 0) <= 60])} grants</div>
                <div class="timeline-item">Later: {len([g for g in all_grants if g.get("enrichment", {}).get("days_remaining", 0) > 60])} grants</div>
            </div>
        </div>
        
        <div class="footer">
            Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 
            <a href="{WIKI_ROOT}/Grants/{active_month()}/active-tracking.md" style="color:#667eea;">View in Obsidian</a> |
            <a href="{GRANTS_ROOT}/dashboard.html" style="color:#667eea;">Full Dashboard</a>
        </div>
    </div>
</body>
</html>"""

    output_dir = GRANTS_ROOT / "outputs" / "tracking" / active_month()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "tracking-dashboard.html"
    with output.open("w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Tracking dashboard generated: {output}")
    return output


if __name__ == "__main__":
    generate_tracking_ui()
