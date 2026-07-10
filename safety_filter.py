"""
Faza 1: Filtri i Sigurisë - eliminon automatikisht coin me sinjale të qarta mashtrimi.
Nëse një coin s'e kalon këtë, REFUZOHET plotësisht, pavarësisht piketës tjetër.
"""

import logging
import config
import sources

log = logging.getLogger("scanner.safety_filter")


def apply_safety_filter(token_data):
    """
    Kthen (passed: bool, reasons: list[str])
    """
    reasons = []

    # Likuiditet minimal
    if token_data.get("liquidity_usd", 0) < config.MIN_LIQUIDITY_USD:
        reasons.append(
            f"Likuiditet nën minimumin (${token_data.get('liquidity_usd', 0):,.0f} < ${config.MIN_LIQUIDITY_USD:,.0f})"
        )

    # Sinjal honeypot klasik: shumë blerje, zero shitje
    buys = token_data.get("txns_24h_buys", 0)
    sells = token_data.get("txns_24h_sells", 0)
    if buys > 20 and sells == 0:
        reasons.append("ZERO shitje me shumë blerje - shenjë e mundshme HONEYPOT")

    # Përqendrimi i mbajtësve (nëse ka të dhëna nga Etherscan/BSCScan)
    holders = sources.get_top_holders(token_data.get("chain", ""), token_data.get("token_address", ""))
    if holders:
        top_pct = sources.calculate_top_holder_pct(holders, token_data.get("total_supply"))
        if top_pct is not None and top_pct > config.MAX_TOP_HOLDER_PCT:
            reasons.append(
                f"Përqendrim i lartë mbajtësish (mbajtësi kryesor ka {top_pct:.1f}% > {config.MAX_TOP_HOLDER_PCT}%)"
            )

    # Luhatje ekstreme çmimi - flamur informativ (s'refuzon vetvetiu, por shënohet)
    price_change = abs(token_data.get("price_change_24h", 0))
    if price_change > 1000:
        reasons.append(f"Luhatje jashtëzakonisht ekstreme çmimi ({price_change:.0f}% në 24h) - dyshim manipulimi")

    passed = len(reasons) == 0
    return passed, reasons
