"""
Crypto Scanner - Skript Kryesor
Vetëm gjetje/analizë e coin-ave të rinj + njoftime. PA trading automatik.

Përdorimi:
    python3 main.py                  # xhirim një herë
    python3 main.py --loop            # xhirim periodik (çdo orë, sipas config.py)
"""

import argparse
import logging
import os
import sys
import time

import config
import database
import sources
import scoring
import telegram_bot
import dashboard


def setup_logging():
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_scan_once():
    log = logging.getLogger("scanner.main")
    log.info("=" * 60)
    log.info("Duke filluar skanimin e ri...")

    all_results = []

    for chain in config.CHAINS:
        log.info(f"Skanim blockchain: {chain}")
        new_pairs = sources.get_new_pairs_dexscreener(chain_id=chain)

        for pair_profile in new_pairs[:config.MAX_RESULTS_PER_SCAN]:
            token_address = pair_profile.get("tokenAddress")
            if not token_address:
                continue

            # Shmang ri-analizë të tepërt brenda 1 ore
            if database.was_recently_scanned(token_address, within_hours=1):
                continue

            pairs = sources.search_pairs_by_token_dexscreener(token_address)
            if not pairs:
                continue

            token_data = sources.extract_token_data(pairs[0])
            if not token_data:
                continue

            result = scoring.analyze_coin(token_data)
            database.save_scan_result(result)
            all_results.append(result)

    passed_results = [r for r in all_results if r.get("passed_safety_filter")]
    passed_results.sort(key=lambda r: r.get("final_score", 0), reverse=True)
    rejected_count = len(all_results) - len(passed_results)

    log.info(f"Skanimi përfundoi: {len(passed_results)} kaluan filtrin, {rejected_count} u refuzuan")

    # Njoftime Telegram
    notified = telegram_bot.notify_if_high_score(passed_results)
    if notified:
        log.info(f"U dërguan {notified} njoftime Telegram")

    # Dashboard
    dashboard_path = dashboard.generate_dashboard(config.DASHBOARD_HTML)
    log.info(f"Dashboard u përditësua: {dashboard_path}")

    # Top 5 në terminal
    if passed_results:
        log.info("--- TOP 5 REZULTATE ---")
        for r in passed_results[:5]:
            log.info(f"  {r['token_symbol']:10s} | {r['final_score']:5.1f}/100 | {r['category']}")

    return passed_results


def main():
    parser = argparse.ArgumentParser(description="Crypto Scanner - gjetje automatike coin-ash me potencial")
    parser.add_argument("--loop", action="store_true", help="Xhiro periodikisht (çdo orë, sipas config.py)")
    args = parser.parse_args()

    setup_logging()
    database.init_database()

    log = logging.getLogger("scanner.main")

    if args.loop:
        log.info(f"Duke xhiruar periodikisht çdo {config.SCAN_INTERVAL_SECONDS} sekonda. Ctrl+C për ndalje.")
        while True:
            try:
                run_scan_once()
                time.sleep(config.SCAN_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                log.info("Ndalur manualisht.")
                break
    else:
        run_scan_once()


if __name__ == "__main__":
    main()
