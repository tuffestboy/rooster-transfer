import os
import json
import time
import requests

INGRESSCOOKIE = os.environ.get("OSIRIS_INGRESSCOOKIE", "")
BEARER_TOKEN = os.environ.get("OSIRIS_BEARER_TOKEN", "")
MANIFEST = os.environ.get("OSIRIS_MANIFEST", "26.30_B354_15ae6a69")
RELEASE_VERSION = os.environ.get(
    "OSIRIS_RELEASE_VERSION", "15ae6a6951cf60ac6c9afc0d100311834f1644f8"
)

VELDEN_VERWIJDEREN = [
    "subonderwerp",
    "actueel",
    "soort_rooster",
    "stoel",
    "locatie_adres",
    "notitie",
    "id_rooster",
    "locatie_y",
    "locatie_x",
    "links",
    "studentnummer",
]


def _cookies():
    return {"INGRESSCOOKIE": INGRESSCOOKIE}


def _headers():
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-GB,en;q=0.8",
        "authorization": f"Bearer {BEARER_TOKEN}",
        "cache-control": "no-cache, no-store, must-revalidate, private",
        "client_type": "web",
        "content-type": "application/json",
        "dnt": "1",
        "manifest": MANIFEST,
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://aventus.osiris-student.nl/rooster",
        "release_version": RELEASE_VERSION,
        "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Brave";v="152"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "taal": "NL",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
        ),
    }


def haal_rooster_op():
    if not INGRESSCOOKIE or not BEARER_TOKEN:
        raise RuntimeError(
            "OSIRIS_INGRESSCOOKIE en/of OSIRIS_BEARER_TOKEN zijn niet ingesteld "
            "(environment variables van de container)."
        )

    params = {"limit": "10"}
    response = requests.get(
        "https://aventus.osiris-student.nl/student/osiris/student/rooster/per_week",
        params=params,
        cookies=_cookies(),
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    for week in data.get("items", []):
        for dag in week.get("dagen", []):
            for les in dag.get("rooster", []):
                for veld in VELDEN_VERWIJDEREN:
                    les.pop(veld, None)

    return data


def scrape_en_opslaan(pad):
    data = haal_rooster_op()
    tijdelijk_pad = pad + ".tmp"
    with open(tijdelijk_pad, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tijdelijk_pad, pad)  #server leest nooit een half-geschreven bestand
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] rooster bijgewerkt -> {pad}", flush=True)


if __name__ == "__main__":
    import sys

    scrape_en_opslaan(sys.argv[1] if len(sys.argv) > 1 else "rooster.json")
