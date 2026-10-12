
import sys
import json
import hashlib
import calendar
from datetime import datetime, timedelta, date, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# ---------- Handmatige CET/CEST-berekening (geen tzdata nodig) ----------

def laatste_zondag(jaar, maand):
    laatste_dag = calendar.monthrange(jaar, maand)[1]
    d = date(jaar, maand, laatste_dag)
    verschil = (d.weekday() - 6) % 7  # weekday(): maandag=0 ... zondag=6
    return d - timedelta(days=verschil)


def is_zomertijd(d):
    """d: een date-object. True als Nederland op die datum in CEST (zomertijd) zit."""
    start = laatste_zondag(d.year, 3)   # laatste zondag maart: CET -> CEST
    einde = laatste_zondag(d.year, 10)  # laatste zondag oktober: CEST -> CET
    return start <= d < einde


def utc_offset_uren(d):
    return 2 if is_zomertijd(d) else 1


# ---------- JSON -> ICS conversie ----------

def parse_tijd(tijd_str):
    uur, minuut = tijd_str.split(":")
    return int(uur), int(minuut)


def lokale_datum_van_dag(datum_iso):
    dt_utc = datetime.fromisoformat(datum_iso.replace("Z", "+00:00")).replace(tzinfo=None)
    kandidaat = (dt_utc + timedelta(hours=2)).date()  # ruwe eerste gok
    offset = utc_offset_uren(kandidaat)
    lokaal = dt_utc + timedelta(hours=offset)
    return lokaal.date()


def maak_utc_datetime(datum_obj, tijd_str):
    uur, minuut = parse_tijd(tijd_str)
    lokaal_naive = datetime(datum_obj.year, datum_obj.month, datum_obj.day, uur, minuut)
    offset = utc_offset_uren(datum_obj)
    return lokaal_naive - timedelta(hours=offset)


def ics_escape(tekst):
    if not tekst:
        return ""
    return (
        tekst.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold_line(line, limit=73):
    if len(line.encode("utf-8")) <= limit:
        return line
    result = []
    while len(line.encode("utf-8")) > limit:
        result.append(line[:limit])
        line = " " + line[limit:]
    result.append(line)
    return "\r\n".join(result)


def maak_event(les, datum_obj):
    onderwerp = les.get("onderwerp") or "Les"
    locatie = les.get("locatie") or ""
    docenten = ", ".join(d.get("naam", "") for d in les.get("docenten", []) if d.get("naam"))

    dt_start_utc = maak_utc_datetime(datum_obj, les["tijd_vanaf"])
    dt_eind_utc = maak_utc_datetime(datum_obj, les["tijd_tm"])

    basis = f"{datum_obj.isoformat()}|{les['tijd_vanaf']}|{les['tijd_tm']}|{onderwerp}"
    uid = hashlib.sha1(basis.encode("utf-8")).hexdigest() + "@rooster-ics"

    regels = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{dt_start_utc.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{dt_eind_utc.strftime('%Y%m%dT%H%M%SZ')}",
        fold_line(f"SUMMARY:{ics_escape(onderwerp)}"),
    ]
    if locatie:
        regels.append(fold_line(f"LOCATION:{ics_escape(locatie)}"))
    if docenten:
        regels.append(fold_line(f"DESCRIPTION:{ics_escape('Docent(en): ' + docenten)}"))
    regels.append("END:VEVENT")
    return regels


def bouw_ics(data):
    regels = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Rooster//NL",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Rooster",
        "X-WR-TIMEZONE:Europe/Amsterdam",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    for week in data.get("items", []):
        for dag in week.get("dagen", []):
            if not dag.get("rooster"):
                continue
            datum_obj = lokale_datum_van_dag(dag["datum"])
            for les in dag["rooster"]:
                if les.get("onderwerp") == "les vervallen":
                    continue
                regels.extend(maak_event(les, datum_obj))
    regels.append("END:VCALENDAR")
    return "\r\n".join(regels) + "\r\n"


# ---------- HTTP server ----------

class Handler(BaseHTTPRequestHandler):
    json_path = "rooster.json"

    def do_GET(self):
        if self.path.rstrip("/") not in ("/rooster.ics", ""):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found. Probeer /rooster.ics")
            return
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ics_inhoud = bouw_ics(data).encode("utf-8")
        except FileNotFoundError:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(
                f"{self.json_path} niet gevonden. Wacht tot de eerste scrape klaar is.".encode("utf-8")
            )
            return
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/calendar; charset=utf-8")
        self.send_header("Content-Disposition", 'inline; filename="rooster.ics"')
        self.send_header("Content-Length", str(len(ics_inhoud)))
        self.end_headers()
        self.wfile.write(ics_inhoud)

    def log_message(self, format, *args):
        pass


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "rooster.json"
    poort = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    Handler.json_path = json_path
    srv = ThreadingHTTPServer(("0.0.0.0", poort), Handler)
    print(f"Serveert {json_path} als ICS op http://0.0.0.0:{poort}/rooster.ics")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
