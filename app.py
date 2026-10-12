import os
import sys
import time
import threading
import traceback

from scraper import scrape_en_opslaan
import server

JSON_PATH = os.environ.get("ROOSTER_JSON_PATH", "/data/rooster.json")
POORT = int(os.environ.get("POORT", "8080"))
INTERVAL_MINUTEN = float(os.environ.get("SCRAPE_INTERVAL_MINUTEN", "15"))


def scrape_loop():
    while True:
        try:
            scrape_en_opslaan(JSON_PATH)
        except Exception:
            print("Fout bij scrapen:", flush=True)
            traceback.print_exc()
        time.sleep(INTERVAL_MINUTEN * 60)


def main():
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)

    scrape_thread = threading.Thread(target=scrape_loop, daemon=True)
    scrape_thread.start()

    server.Handler.json_path = JSON_PATH
    srv = server.ThreadingHTTPServer(("0.0.0.0", POORT), server.Handler)
    print(
        f"ICS-feed beschikbaar op http://0.0.0.0:{POORT}/rooster.ics "
        f"(scrape elke {INTERVAL_MINUTEN} min, bron: {JSON_PATH})",
        flush=True,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
