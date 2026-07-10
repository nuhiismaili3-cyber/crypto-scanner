"""
Konfigurimi qendror - Crypto Scanner (vetëm gjetje/analizë, PA trading automatik)
"""

import os

# ============================================================
# API KEYS (vendosi si variabla mjedisi - kurrë mos i shkruaj këtu)
# ============================================================
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")              # opsionale
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Burime pa kyç (falas plotësisht): DEX Screener, CoinGecko, RSS exchange feeds

# ============================================================
# BLOCKCHAIN-ET DHE PARAMETRAT E KËRKIMIT
# ============================================================
CHAINS = ["ethereum", "bsc", "solana"]
MAX_COIN_AGE_HOURS = 72
MIN_LIQUIDITY_USD = 10000
MAX_RESULTS_PER_SCAN = 50
SCAN_INTERVAL_SECONDS = 300           # 5 minuta

# ============================================================
# FAZA 1 - FILTRI I SIGURISË (eliminim automatik nëse dështon)
# ============================================================
MAX_TOP_HOLDER_PCT = 35.0
MIN_LIQUIDITY_LOCK_DAYS = 30

# ============================================================
# FAZA 2 - PESHAT E SCORING (sipas planit të ri me 6 kategori)
# ============================================================
WEIGHTS = {
    "community": 20,          # rritja e komunitetit (Reddit, GitHub stars)
    "volume_liquidity": 20,    # volumi dhe likuiditeti
    "listing_potential": 20,   # sinjale listimi (RSS exchange, launchpad)
    "dev_activity": 15,        # aktiviteti i zhvilluesve (GitHub commits)
    "contract_safety": 15,     # siguria e kontratës
    "risk": 10,                # faktorë rreziku (invers - më pak risk = më shumë pikë)
}

# ============================================================
# KATEGORITË E POTENCIALIT (zëvendëson "% pump i pritur")
# ============================================================
POTENTIAL_CATEGORIES = [
    (80, 100, "🟢🟢 SINJAL I FORTË"),
    (65, 80, "🟢 INTERESANT"),
    (40, 65, "🟡 VËZHGIM"),
    (0, 40, "🔴 RREZIK I LARTË / POTENCIAL I ULËT"),
]

# Njofto në Telegram vetëm nëse piketa kalon këtë prag
NOTIFY_SCORE_THRESHOLD = 65

# ============================================================
# DATABAZA
# ============================================================
DATABASE_PATH = "crypto_scanner.db"

# ============================================================
# OUTPUT
# ============================================================
OUTPUT_DIR = "output"
DASHBOARD_HTML = f"{OUTPUT_DIR}/dashboard.html"
LOG_FILE = f"{OUTPUT_DIR}/scanner.log"
