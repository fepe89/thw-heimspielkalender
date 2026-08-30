# Dauerhafter THW-Kiel-Heimspielkalender

Das Skript liest den offiziellen Saisonplan des THW Kiel, filtert ausschließlich
Begegnungen mit „THW Kiel“ als Heimteam und erzeugt eine dauerhaft abonnierbare
iCalendar-Datei. Die Saison wird automatisch aus dem Datum ermittelt; zur
laufenden wird auch eine bereits veröffentlichte Folgesaison geprüft.
Austragungsort ist die **MERKUR Ostseehalle
(ehemals Wunderino Arena), Europaplatz 1, 24103 Kiel**.

## Enthaltene Termine

- alle Pflicht-Heimspiele der laufenden Saison, die im offiziellen Plan stehen
- automatischer Saisonwechsel im Juli, ohne Änderung am Skript oder an der Abo-URL
- früh veröffentlichte Spiele der Folgesaison schon vor dem Saisonwechsel
- bestätigte Termine mit Anstoßzeit und zweistündiger Dauer
- noch nicht endgültig terminierte Spieltage als vorläufige Ganztagstermine
- später ergänzte Pokal-Heimspiele automatisch, sobald sie im Saisonplan stehen
- keine Auswärtsspiele und keine Vorbereitungsspiele vor dem Saisonstart

Offizielle Quellen:

- Saisonplan-Schema: `https://archiv.thw-handball.de/thw/JJtermin.htm`
- aktuelle THW-Termine: https://thw-handball.de/service/termine/
- Hallenanschrift: https://thw-handball.de/tickets/wunderino-arena/

## Lokal aktualisieren

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python update_calendar.py
```

Die fertige Datei heißt immer `thw-kiel-heimspiele.ics`. Dieser unveränderte
Name ist wichtig, damit ein bestehendes Kalenderabonnement über Saisonwechsel
hinweg weiterläuft.

## Automatische Aktualisierung mit GitHub

1. Den gesamten Ordner in ein GitHub-Repository hochladen.
2. Unter **Settings > Actions > General > Workflow permissions** die Option
   **Read and write permissions** aktivieren.
3. Die mitgelieferte GitHub-Automation läuft täglich und schreibt Änderungen
   direkt in das Repository.
   Ein wöchentlicher Aktivitätsnachweis verhindert, dass GitHub die geplante
   Ausführung nach längerer Zeit ohne Spielplanänderungen deaktiviert.
4. Für ein wirkliches Kalender-Abo GitHub Pages für den Repository-Ordner
   aktivieren oder die Raw-Datei abonnieren:

```text
https://raw.githubusercontent.com/BENUTZER/REPOSITORY/main/thw-kiel-heimspiele.ics
```

Apple Kalender: **Ablage > Neues Kalenderabonnement** und die URL einfügen.
Auf iPhone/iPad: **Einstellungen > Apps > Kalender > Kalenderaccounts >
Account hinzufügen > Andere > Kalenderabo hinzufügen**.

Hinweis: Kalender-Apps bestimmen selbst, wie oft sie abonnierte Kalender neu
laden. Die Datei fordert mit `REFRESH-INTERVAL:P1D` eine tägliche Aktualisierung
an.
