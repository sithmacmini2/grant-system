#!/usr/bin/env python3
"""
Dashboard Generator - Creates HTML dashboard from grant data
"""

import json
import os
from datetime import datetime

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"


def load_grants():
    """Load enriched grants"""
    f = f"{GRANTS_ROOT}/data/enriched/2026-04/grants-enriched.json"
    if os.path.exists(f):
        with open(f) as fp:
            return json.load(fp)
    return []


def generate_dashboard():
    """Generate HTML dashboard"""
    grants = load_grants()

    if not grants:
        print("No grant data found. Run monthly-research.py first.")
        return

    sorted_grants = sorted(
        grants,
        key=lambda g: g.get("intelligence", {}).get("fit_score", 0),
        reverse=True,
    )

    total_amount = sum(g.get("amount", 0) for g in grants)
    high_fit = len(
        [g for g in grants if g.get("intelligence", {}).get("fit_score", 0) >= 6]
    )
    urgent = len(
        [g for g in grants if g.get("enrichment", {}).get("urgency_level") == "HIGH"]
    )
    proposals = len(
        [g for g in grants if g.get("intelligence", {}).get("fit_score", 0) >= 6]
    )

    alerts_html = ""
    for g in sorted_grants:
        if g.get("enrichment", {}).get("urgency_level") == "HIGH":
            days = g.get("enrichment", {}).get("days_remaining", 0)
            fit = g.get("intelligence", {}).get("fit_score", 0)
            rec = g.get("intelligence", {}).get("recommendation", "Track")
            fit_class = (
                "fit-high" if fit >= 6 else "fit-medium" if fit >= 4 else "fit-low"
            )
            alerts_html += f"""
            <tr>
                <td>{g.get("name", "")[:40]}</td>
                <td>{g.get("funder", "")[:25]}</td>
                <td>${g.get("amount", 0):,}</td>
                <td><span class="badge badge-high">{days} days</span></td>
                <td class="{fit_class}">{fit}/10</td>
                <td>{rec}</td>
            </tr>"""

    if not alerts_html:
        alerts_html = "<tr><td colspan='6'>No urgent deadlines</td></tr>"

    grants_html = ""
    for i, g in enumerate(sorted_grants[:15], 1):
        days = g.get("enrichment", {}).get("days_remaining", 0)
        fit = g.get("intelligence", {}).get("fit_score", 0)
        rec = g.get("intelligence", {}).get("recommendation", "Track")
        fit_class = "fit-high" if fit >= 6 else "fit-medium" if fit >= 4 else "fit-low"
        grants_html += f"""
            <tr><td>{i}</td><td>{g.get("name", "")[:35]}</td><td>{g.get("funder", "")[:20]}</td>
            <td>${g.get("amount", 0):,}</td><td>{g.get("deadline", "")}</td>
            <td class="{fit_class}">{fit}/10</td><td>{rec}</td></tr>"""

    proposals_html = ""
    for g in sorted_grants:
        if g.get("intelligence", {}).get("fit_score", 0) >= 6:
            proposals_html += f"""
            <tr><td>{g.get("name", "")[:40]}</td><td>{g.get("funder", "")[:25]}</td>
            <td>${g.get("amount", 0):,}</td><td>Template Ready</td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MUSE Foundation - Grant Intelligence Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #16213e; border-radius: 15px; padding: 25px; text-align: center; }}
        .stat-number {{ font-size: 3rem; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .section {{ background: #16213e; border-radius: 15px; padding: 25px; margin-bottom: 20px; }}
        .section h2 {{ color: #667eea; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #2a2a4a; }}
        th {{ background: #0f3460; }}
        tr:hover {{ background: #1f4068; }}
        .fit-high {{ color: #4ade80; font-weight: bold; }}
        .fit-medium {{ color: #fbbf24; }}
        .fit-low {{ color: #f87171; }}
        .badge {{ padding: 5px 10px; border-radius: 20px; font-size: 0.8rem; }}
        .badge-high {{ background: #dc2626; }}
        .btn {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; margin: 5px; }}
        .nav {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
        .nav a {{ padding: 10px 20px; background: #16213e; color: #667eea; text-decoration: none; border-radius: 8px; }}
        .nav a:hover {{ background: #667eea; color: white; }}
        .actions {{ text-align: center; margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Grant Intelligence Dashboard</h1>
        <p>The MUSE Foundation of Rhode Island</p>
    </div>
    <div class="container">
        <div class="nav">
            <a href="#overview">Overview</a>
            <a href="#grants">All Grants</a>
            <a href="#alerts">Urgent</a>
            <a href="#proposals">Proposals</a>
        </div>
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{len(grants)}</div><div class="stat-label">Total Grants</div></div>
            <div class="stat-card"><div class="stat-number">{high_fit}</div><div class="stat-label">High Priority</div></div>
            <div class="stat-card"><div class="stat-number">{urgent}</div><div class="stat-label">Urgent</div></div>
            <div class="stat-card"><div class="stat-number">${total_amount / 1000:.0f}k</div><div class="stat-label">Total Available</div></div>
        </div>
        <div class="actions">
            <a href="/home/sithmm2_admin/wiki/Grants/2026/04-Active-Tracking.md" class="btn">📊 View Full Dashboard</a>
            <a href="file:///home/sithmm2_admin/grants-system/outputs/matrix/2026-04/2026-04-grant-matrix.csv" class="btn">📋 Download CSV</a>
            <a href="#" class="btn" onclick="location.reload()">🔄 Refresh</a>
        </div>
        <div class="section" id="alerts">
            <h2>⚠️ Deadline Alerts (Due within 14 days)</h2>
            <table>
                <tr><th>Grant</th><th>Funder</th><th>Amount</th><th>Days</th><th>Fit</th><th>Action</th></tr>
                {alerts_html}
            </table>
        </div>
        <div class="section" id="grants">
            <h2>📋 All Grants (Ranked by Fit Score)</h2>
            <table>
                <tr><th>#</th><th>Grant</th><th>Funder</th><th>Amount</th><th>Deadline</th><th>Fit</th><th>Rec</th></tr>
                {grants_html}
            </table>
        </div>
        <div class="section" id="proposals">
            <h2>📝 Generated Proposal Drafts (Fit 6+)</h2>
            <table>
                <tr><th>Grant</th><th>Funder</th><th>Amount</th><th>Status</th></tr>
                {proposals_html}
            </table>
        </div>
    </div>
</body>
</html>"""

    output = f"{GRANTS_ROOT}/dashboard.html"
    with open(output, "w") as f:
        f.write(html)

    print(f"✅ Dashboard generated: {output}")
    return output


if __name__ == "__main__":
    generate_dashboard()
