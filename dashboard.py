"""
Gjeneron dashboard HTML statik nga rezultatet e ruajtura në databazë.
"""

from datetime import datetime, timezone
import database


def _category_color(category):
    if "FORTË" in category:
        return "#22c55e"
    elif "INTERESANT" in category:
        return "#4ade80"
    elif "VËZHGIM" in category:
        return "#eab308"
    else:
        return "#ef4444"


def _render_coin_card(row):
    import json
    color = _category_color(row.get("category", ""))
    component_scores = json.loads(row.get("component_scores", "{}") or "{}")
    components_html = "".join(
        f'<div class="component"><span>{key.replace("_", " ").title()}</span>'
        f'<div class="bar"><div class="bar-fill" style="width:{val}%"></div></div>'
        f'<span>{val}</span></div>'
        for key, val in component_scores.items()
    )

    return f"""
    <div class="coin-card">
        <div class="coin-header">
            <div>
                <h3>{row['token_symbol']} <span class="token-name">{row.get('token_name', '')}</span></h3>
                <span class="chain-badge">{row.get('chain', '')}</span>
            </div>
            <div class="score-circle" style="border-color:{color}; color:{color}">
                {row['final_score']}
            </div>
        </div>
        <div class="category-label" style="color:{color}">{row.get('category', '')}</div>
        <div class="coin-stats">
            <div><strong>Likuiditet:</strong> ${row.get('liquidity_usd', 0):,.0f}</div>
            <div><strong>Volum 24h:</strong> ${row.get('volume_24h', 0):,.0f}</div>
        </div>
        <div class="components">{components_html}</div>
    </div>
    """


def generate_dashboard(output_path):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    results = database.get_top_results(limit=30, min_score=0)
    cards = "".join(_render_coin_card(r) for r in results)

    html = f"""<!DOCTYPE html>
<html lang="sq">
<head>
<meta charset="UTF-8">
<title>Crypto Scanner Dashboard</title>
<style>
    body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
    h1 {{ font-size: 24px; margin-bottom: 4px; }}
    .timestamp {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
    .coin-card {{ background: #1e293b; border-radius: 12px; padding: 16px; border: 1px solid #334155; }}
    .coin-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px; }}
    .coin-header h3 {{ margin: 0; font-size: 18px; }}
    .token-name {{ font-weight: normal; color: #94a3b8; font-size: 13px; }}
    .chain-badge {{ display: inline-block; background: #334155; padding: 2px 8px; border-radius: 6px; font-size: 11px; margin-top: 4px; }}
    .score-circle {{ width: 48px; height: 48px; border-radius: 50%; border: 3px solid; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; }}
    .category-label {{ font-size: 13px; font-weight: bold; margin-bottom: 12px; }}
    .coin-stats {{ display: flex; gap: 16px; font-size: 13px; margin-bottom: 12px; color: #cbd5e1; }}
    .components {{ display: flex; flex-direction: column; gap: 6px; }}
    .component {{ display: grid; grid-template-columns: 130px 1fr 30px; align-items: center; gap: 8px; font-size: 12px; }}
    .bar {{ background: #334155; border-radius: 4px; height: 6px; overflow: hidden; }}
    .bar-fill {{ background: #60a5fa; height: 100%; }}
</style>
</head>
<body>
    <h1>🔍 Crypto Scanner Dashboard</h1>
    <div class="timestamp">Përditësuar: {timestamp} · {len(results)} rezultate (24 orët e fundit)</div>
    <div class="grid">
        {cards if cards else '<p>Ende s\'ka rezultate. Xhiro main.py për të filluar skanimin.</p>'}
    </div>
</body>
</html>
"""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
