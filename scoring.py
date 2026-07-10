"""
Faza 2: Motori i Scoring-ut - piketë e peshuar 0-100, konvertuar në
Kategori Potenciali (jo "% pump i pritur" - siç u vendos).
Përfshin edhe Momentum Score (a po përshpejtohet interesi krahasuar me skanimin e fundit).
"""

import logging

import config
import sources
import database

log = logging.getLogger("scanner.scoring")


def get_potential_category(score):
    for low, high, label in config.POTENTIAL_CATEGORIES:
        if low <= score < high or (high == 100 and score == 100):
            return label
    return "🔴 RREZIK I LARTË / POTENCIAL I ULËT"


def calculate_volume_liquidity_score(token_data):
    """Komponenti 'volume_liquidity' - kombinon madhësinë e likuiditetit dhe pattern-in e volumit."""
    liq = token_data.get("liquidity_usd", 0)
    if liq < config.MIN_LIQUIDITY_USD:
        liq_score = 0
    elif liq < 25000:
        liq_score = 40
    elif liq < 100000:
        liq_score = 65
    elif liq < 500000:
        liq_score = 85
    else:
        liq_score = 100

    # Pattern volumi: krahason volumin 1h me mesataren e pritur
    volume_24h = token_data.get("volume_24h", 0)
    volume_1h = token_data.get("volume_1h", 0)
    hourly_avg = volume_24h / 24 if volume_24h else 0
    ratio = volume_1h / hourly_avg if hourly_avg > 0 else 0

    if ratio > 10:
        pattern_score = 20   # spike shumë i fortë - dyshimtë
    elif ratio > 5:
        pattern_score = 50
    elif ratio > 1.5:
        pattern_score = 80
    else:
        pattern_score = 65

    return round((liq_score + pattern_score) / 2)


def calculate_community_score(community_data):
    """Komponenti 'community' - bazuar në Reddit subscribers, GitHub stars."""
    reddit_subs = community_data.get("reddit_subscribers", 0)
    stars = community_data.get("github_stars", 0)

    score = 0
    score += min(reddit_subs / 50, 50)    # deri 50 pikë
    score += min(stars / 2, 50)            # deri 50 pikë
    return round(min(score, 100))


def calculate_listing_potential_score(token_data, rss_mentions):
    """Komponenti 'listing_potential' - bazuar në përmendje RSS exchange."""
    if rss_mentions:
        return 90   # u përmend direkt në njoftim exchange - sinjal shumë i fortë
    # Pa RSS mentions, japim piketë neutrale-mesatare (s'kemi Twitter/launchpad tracking ende - faza 2)
    return 35


def calculate_dev_activity_score(dev_data):
    """Komponenti 'dev_activity' - GitHub commits + stars."""
    if not dev_data.get("repo_found"):
        return 20   # s'ka repo publik - jo automatikisht negativ, por e ulët
    commits = dev_data.get("commits_30d", 0)
    stars = dev_data.get("stars", 0)
    score = min(commits * 3, 60) + min(stars / 5, 40)
    return round(min(score, 100))


def calculate_contract_safety_score(chain, token_address):
    """Komponenti 'contract_safety' - a është kontrata e verifikuar publikisht."""
    verification = sources.get_contract_verification(chain, token_address)
    if verification is None:
        return 40   # e panjohur (s'ka API key ndoshta) - neutrale
    return 90 if verification.get("is_verified") else 20


def calculate_risk_score(token_data, risk_flags):
    """Komponenti 'risk' - invers: më pak flamuj risku = piketë më e lartë."""
    base = 100
    base -= len(risk_flags) * 20
    if token_data.get("liquidity_usd", 0) < 25000:
        base -= 15
    return max(round(base), 0)


def calculate_momentum(token_address, current_score, current_liquidity, current_volume):
    """
    Krahason me skanimin e fundit të mëparshëm për të matur nëse interesi
    po përshpejtohet apo ngadalësohet. Kthen: 'up', 'down', 'stable', ose 'new'.
    """
    previous = database.get_previous_scan(token_address)
    if not previous:
        return "new"

    score_diff = current_score - previous.get("final_score", 0)
    volume_diff_pct = (
        ((current_volume - previous.get("volume_24h", 0)) / previous.get("volume_24h", 1)) * 100
        if previous.get("volume_24h", 0) > 0 else 0
    )

    if score_diff > 5 or volume_diff_pct > 20:
        return "📈 në rritje"
    elif score_diff < -5 or volume_diff_pct < -20:
        return "📉 në rënie"
    else:
        return "➡️ stabël"


def analyze_coin(token_data):
    """Analiza e plotë: Faza 1 + Faza 2. Kthen dict me rezultatin e plotë."""
    import safety_filter

    result = {
        "token_address": token_data.get("token_address"),
        "token_symbol": token_data.get("token_symbol"),
        "token_name": token_data.get("token_name"),
        "chain": token_data.get("chain"),
        "price_usd": token_data.get("price_usd"),
        "liquidity_usd": token_data.get("liquidity_usd"),
        "volume_24h": token_data.get("volume_24h"),
        "dex_url": token_data.get("dex_url"),
    }

    # -------- FAZA 1 --------
    passed, reasons = safety_filter.apply_safety_filter(token_data)
    result["passed_safety_filter"] = passed
    result["rejection_reasons"] = reasons

    if not passed:
        result["final_score"] = 0
        result["category"] = "❌ REFUZUAR (Faza 1)"
        return result

    # -------- FAZA 2 --------
    project_name = token_data.get("token_name", "")

    community_data = sources.extract_community_data(None)  # placeholder nëse s'kemi CoinGecko ID
    rss_mentions = sources.check_exchange_rss_for_token(
        token_data.get("token_symbol", ""), token_data.get("token_name", "")
    )
    dev_data = sources.evaluate_dev_activity(project_name)

    risk_flags = []
    if token_data.get("liquidity_usd", 0) < 25000:
        risk_flags.append("Likuiditet relativisht i ulët - luhatshmëri e lartë e pritshme")
    if abs(token_data.get("price_change_24h", 0)) > 100:
        risk_flags.append(f"Luhatje e lartë çmimi 24h ({token_data.get('price_change_24h', 0):.0f}%)")
    if not dev_data.get("repo_found"):
        risk_flags.append("S'u gjet repo publik GitHub")

    component_scores = {
        "community": calculate_community_score(community_data),
        "volume_liquidity": calculate_volume_liquidity_score(token_data),
        "listing_potential": calculate_listing_potential_score(token_data, rss_mentions),
        "dev_activity": calculate_dev_activity_score(dev_data),
        "contract_safety": calculate_contract_safety_score(
            token_data.get("chain", ""), token_data.get("token_address", "")
        ),
        "risk": calculate_risk_score(token_data, risk_flags),
    }

    total_weight = sum(config.WEIGHTS.values())
    weighted_sum = sum(
        component_scores.get(key, 0) * weight
        for key, weight in config.WEIGHTS.items()
    )
    final_score = round(weighted_sum / total_weight, 1)

    momentum = calculate_momentum(
        token_data.get("token_address"), final_score,
        token_data.get("liquidity_usd", 0), token_data.get("volume_24h", 0)
    )

    result["component_scores"] = component_scores
    result["final_score"] = final_score
    result["category"] = get_potential_category(final_score)
    result["momentum"] = momentum
    result["risk_flags"] = risk_flags
    result["rss_mentions"] = rss_mentions

    log.info(f"{token_data.get('token_symbol')}: piketë {final_score}/100 - {result['category']} - momentum: {momentum}")
    return result
