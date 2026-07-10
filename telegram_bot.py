"""
Njoftime Telegram - dërgon alarme kur gjendet coin me piketë të lartë.
Kërkon: bot token nga @BotFather + chat_id (grup ose bisedë personale).
"""

import html
import logging
import requests

import config
import database

log = logging.getLogger("scanner.telegram")


def send_telegram_message(text):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        log.warning("Telegram s'është konfiguruar - njoftimi anashkalohet.")
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error(f"Gabim dërgimi Telegram: {e}")
        return False


def format_coin_alert(result):
    """Formaton mesazhin e njoftimit sipas kërkesës origjinale:
    emri, arsyet e piketës, rreziqet, burimet."""

    esc = html.escape

    lines = [
        f"🔍 <b>{esc(str(result['token_symbol']))}</b> ({esc(str(result['token_name']))})",
        f"Kategoria: <b>{esc(str(result['category']))}</b>",
        f"Piketë: <b>{result['final_score']}/100</b>",
        f"Momentum: {esc(str(result.get('momentum', 'N/A')))}",
        "",
        "<b>Pse mori këtë piketë:</b>",
    ]

    components = result.get("component_scores", {})
    labels = {
        "community": "Komuniteti",
        "volume_liquidity": "Volum/Likuiditet",
        "listing_potential": "Potenciali listimit",
        "dev_activity": "Aktiviteti zhvillimit",
        "contract_safety": "Siguria e kontratës",
        "risk": "Rreziku (invers)",
    }
    for key, val in components.items():
        lines.append(f"  • {labels.get(key, key)}: {val}/100")

    if result.get("risk_flags"):
        lines.append("")
        lines.append("<b>⚠️ Flamuj Risku:</b>")
        for flag in result["risk_flags"]:
            lines.append(f"  • {esc(str(flag))}")

    lines.append("")
    lines.append(f"Blockchain: {esc(str(result['chain']))} | Likuiditet: ${result['liquidity_usd']:,.0f}")
    lines.append(f"🔗 <a href=\"{esc(str(result.get('dex_url', '#')))}\">Shiko në DEX Screener</a>")

    if result.get("rss_mentions"):
        lines.append("")
        lines.append("<b>📰 Përmendur në njoftime exchange:</b>")
        for mention in result["rss_mentions"]:
            lines.append(f"  • {esc(str(mention['exchange']))}: {esc(str(mention['title']))}")

    return "\n".join(lines)


def notify_if_high_score(results):
    """Dërgon njoftim vetëm për coin që kalojnë pragun, dhe vetëm nëse s'u njoftuan tashmë."""
    notified_count = 0
    for result in results:
        if result.get("final_score", 0) < config.NOTIFY_SCORE_THRESHOLD:
            continue
        if database.was_notified_recently(result["token_address"]):
            continue

        message = format_coin_alert(result)
        if send_telegram_message(message):
            notified_count += 1
            log.info(f"Njoftim dërguar për {result['token_symbol']}")

    return notified_count
