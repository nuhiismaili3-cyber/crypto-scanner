"""
Të gjitha burimet e të dhënave në një modul (strukturë e thjeshtuar).
Të gjitha FALAS - disa kërkojnë regjistrim (Etherscan, Reddit), të tjera jo.
"""

import logging
import requests
import feedparser
from datetime import datetime, timedelta, timezone

import config

log = logging.getLogger("scanner.sources")


# ============================================================
# DEX SCREENER (falas, pa kyç)
# ============================================================

def get_new_pairs_dexscreener(chain_id="ethereum"):
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [d for d in data if d.get("chainId") == chain_id]
    except requests.RequestException as e:
        log.error(f"DEX Screener gabim: {e}")
        return []


def search_pairs_by_token_dexscreener(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("pairs", [])
    except requests.RequestException as e:
        log.error(f"DEX Screener gabim kërkimi: {e}")
        return []


def extract_token_data(pair):
    if not pair:
        return None
    return {
        "token_address": pair.get("baseToken", {}).get("address"),
        "token_name": pair.get("baseToken", {}).get("name"),
        "token_symbol": pair.get("baseToken", {}).get("symbol"),
        "chain": pair.get("chainId"),
        "price_usd": float(pair.get("priceUsd", 0) or 0),
        "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
        "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
        "volume_1h": float(pair.get("volume", {}).get("h1", 0) or 0),
        "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0) or 0),
        "txns_24h_buys": pair.get("txns", {}).get("h24", {}).get("buys", 0),
        "txns_24h_sells": pair.get("txns", {}).get("h24", {}).get("sells", 0),
        "pair_created_at": pair.get("pairCreatedAt"),
        "fdv": float(pair.get("fdv", 0) or 0),
        "dex_url": pair.get("url"),
    }


# ============================================================
# COINGECKO (falas me rate limit)
# ============================================================

def get_coin_details_coingecko(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {"localization": "false", "tickers": "false",
              "community_data": "true", "developer_data": "true"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.error(f"CoinGecko gabim: {e}")
        return None


def extract_community_data(coin_data):
    if not coin_data:
        return {"reddit_subscribers": 0, "twitter_followers": 0,
                "github_stars": 0, "commits_4_weeks": 0}
    community = coin_data.get("community_data", {}) or {}
    developer = coin_data.get("developer_data", {}) or {}
    return {
        "reddit_subscribers": community.get("reddit_subscribers", 0) or 0,
        "twitter_followers": community.get("twitter_followers", 0) or 0,
        "github_stars": developer.get("stars", 0) or 0,
        "commits_4_weeks": developer.get("commit_count_4_weeks", 0) or 0,
    }


# ============================================================
# ETHERSCAN / BSCSCAN (falas me regjistrim)
# ============================================================

_ENDPOINTS = {
    "ethereum": "https://api.etherscan.io/api",
    "bsc": "https://api.bscscan.com/api",
}


def _get_scan_api_key(chain):
    return config.ETHERSCAN_API_KEY if chain == "ethereum" else config.BSCSCAN_API_KEY


def get_top_holders(chain, token_address, limit=10):
    base_url = _ENDPOINTS.get(chain)
    api_key = _get_scan_api_key(chain)
    if not base_url or not api_key:
        return []
    params = {
        "module": "token", "action": "tokenholderlist",
        "contractaddress": token_address, "page": 1, "offset": limit,
        "apikey": api_key,
    }
    try:
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", []) if data.get("status") == "1" else []
    except requests.RequestException as e:
        log.error(f"Etherscan/BSCScan gabim: {e}")
        return []


def calculate_top_holder_pct(holders, total_supply=None):
    if not holders or not total_supply:
        return None
    try:
        top_balance = float(holders[0].get("TokenHolderQuantity", 0))
        return (top_balance / total_supply) * 100
    except (ValueError, TypeError, IndexError):
        return None


def get_contract_verification(chain, token_address):
    base_url = _ENDPOINTS.get(chain)
    api_key = _get_scan_api_key(chain)
    if not base_url or not api_key:
        return None
    params = {"module": "contract", "action": "getsourcecode",
              "address": token_address, "apikey": api_key}
    try:
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("result", [{}])[0]
        return {"is_verified": bool(result.get("SourceCode"))}
    except requests.RequestException as e:
        log.error(f"Kontroll kontrate gabim: {e}")
        return None


# ============================================================
# GITHUB (falas)
# ============================================================

def _github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


def search_github_repo(project_name):
    url = "https://api.github.com/search/repositories"
    params = {"q": project_name, "sort": "stars", "order": "desc", "per_page": 3}
    try:
        resp = requests.get(url, params=params, headers=_github_headers(), timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0] if items else None
    except requests.RequestException as e:
        log.error(f"GitHub gabim kërkimi: {e}")
        return None


def get_commit_count(owner, repo, days=30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"since": since, "per_page": 100}
    try:
        resp = requests.get(url, params=params, headers=_github_headers(), timeout=10)
        resp.raise_for_status()
        commits = resp.json()
        return len(commits) if isinstance(commits, list) else 0
    except requests.RequestException as e:
        log.error(f"GitHub gabim commits: {e}")
        return 0


def evaluate_dev_activity(project_name):
    repo = search_github_repo(project_name)
    if not repo:
        return {"repo_found": False, "commits_30d": 0, "stars": 0, "contributors": 0}
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    return {
        "repo_found": True,
        "commits_30d": get_commit_count(owner, repo_name),
        "stars": repo.get("stargazers_count", 0),
        "repo_url": repo.get("html_url"),
    }


# ============================================================
# REDDIT (falas me regjistrim)
# ============================================================

def _reddit_token():
    if not config.REDDIT_CLIENT_ID or not config.REDDIT_CLIENT_SECRET:
        return None
    auth = (config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET)
    headers = {"User-Agent": "crypto-scanner-bot/1.0"}
    try:
        resp = requests.post("https://www.reddit.com/api/v1/access_token",
                              auth=auth, data={"grant_type": "client_credentials"},
                              headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("access_token")
    except requests.RequestException as e:
        log.error(f"Reddit auth gabim: {e}")
        return None


def search_reddit_mentions(token_symbol, token_name, limit=50):
    token = _reddit_token()
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "crypto-scanner-bot/1.0"}
    query = f'{token_symbol} OR "{token_name}"'
    params = {"q": query, "sort": "new", "limit": limit, "t": "week"}
    try:
        resp = requests.get("https://oauth.reddit.com/search", headers=headers,
                             params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("children", [])
    except requests.RequestException as e:
        log.error(f"Reddit kërkim gabim: {e}")
        return []


# ============================================================
# RSS EXCHANGE ANNOUNCEMENTS (falas)
# ============================================================

# Feed-e RSS publike të njohura - duhet verifikuar periodikisht nëse mbeten aktive
EXCHANGE_RSS_FEEDS = {
    "kraken": "https://blog.kraken.com/feed",
    # Shënim: Binance/OKX/Bybit s'kanë RSS zyrtar të qëndrueshëm për "new listings" -
    # këto zakonisht kërkojnë web scraping ose Claude+web search (faza 2)
}


def check_exchange_rss_for_token(token_symbol, token_name):
    """Kontrollon nëse token-i përmendet në ndonjë RSS feed exchange të fundit."""
    mentions = []
    for exchange, feed_url in EXCHANGE_RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "").lower()
                if token_symbol.lower() in title or token_name.lower() in title:
                    mentions.append({"exchange": exchange, "title": entry.get("title"),
                                      "link": entry.get("link")})
        except Exception as e:
            log.error(f"RSS gabim për {exchange}: {e}")
    return mentions
