#!/usr/bin/env python3
"""Erzeugt dauerhaft einen ICS-Kalender mit den THW-Kiel-Heimspielen."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

SOURCE_TEMPLATE = "https://archiv.thw-handball.de/thw/{year:02d}termin.htm"
OUTPUT = Path(__file__).with_name("thw-kiel-heimspiele.ics")
LOCATION = "MERKUR Ostseehalle, Europaplatz 1, 24103 Kiel"
USER_AGENT = "THW-Heimspielkalender/1.0 (+private calendar generator)"


@dataclass(frozen=True)
class Match:
    season_start_year: int
    source_url: str
    day: date
    time: str | None
    competition: str
    opponent: str
    provisional: bool
    result: str | None = None


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def parse_day(text: str) -> date | None:
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
    return datetime.strptime(match.group(1), "%d.%m.%Y").date() if match else None


def current_season_start_year(today: date | None = None) -> int:
    """Liefert für Juli bis Dezember das laufende, sonst das Vorjahr."""
    today = today or datetime.now(ZoneInfo("Europe/Berlin")).date()
    return today.year if today.month >= 7 else today.year - 1


def source_url(season_start_year: int) -> str:
    return SOURCE_TEMPLATE.format(year=season_start_year % 100)


def parse_matches(html: str, season_start_year: int, url: str) -> list[Match]:
    # Die historische THW-Seite enthält altes HTML ohne schließende </td>-Tags.
    # Der lxml-Parser rekonstruiert die Tabellenzeilen zuverlässig.
    soup = BeautifulSoup(html, "lxml")
    matches: list[Match] = []
    season_start = date(season_start_year, 7, 1)
    season_end = date(season_start_year + 1, 6, 30)

    for row in soup.select("tr.match"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        date_text = clean(cells[0].get_text(" ", strip=True))
        competition = clean(cells[2].get_text(" ", strip=True))
        fixture = clean(cells[3].get_text(" ", strip=True))
        day = parse_day(date_text)

        if not day or not (season_start <= day <= season_end):
            continue

        # Vorbereitungsspiele gehören nicht zum Pflichtspielkalender.
        if competition.upper().startswith("VB"):
            continue

        # Nur echte Heimspiele: THW muss links vom Trennstrich stehen.
        fixture_match = re.match(r"^THW Kiel\s*-\s*(.+?)(?::\s*\d|$)", fixture)
        if not fixture_match:
            continue

        opponent = clean(fixture_match.group(1))
        opponent = re.sub(r"\s*\(noch nicht terminiert\)\s*$", "", opponent)
        provisional = "noch nicht terminiert" in fixture.lower()

        time_match = re.search(r",\s*(\d{2})\.(\d{2})\s*$", date_text)
        time_value = None
        if time_match and time_match.group(0) != ", 00.00" and not provisional:
            time_value = f"{time_match.group(1)}:{time_match.group(2)}"

        result_match = re.search(r":\s*(\d+:\d+)", fixture)
        matches.append(
            Match(
                season_start_year=season_start_year,
                source_url=url,
                day=day,
                time=time_value,
                competition=competition,
                opponent=opponent,
                provisional=provisional,
                result=result_match.group(1) if result_match else None,
            )
        )

    return sorted(set(matches), key=lambda item: (item.day, item.time or "", item.opponent))


def ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\n", r"\n")
    )


def fold(line: str) -> str:
    """Faltet eine ICS-Zeile auf maximal 75 UTF-8-Bytes."""
    parts: list[str] = []
    remaining = line
    first = True
    limit = 75
    while len(remaining.encode("utf-8")) > limit:
        size = limit
        while len(remaining[:size].encode("utf-8")) > limit:
            size -= 1
        while size < len(remaining) and len(remaining[: size + 1].encode("utf-8")) <= limit:
            size += 1
        parts.append(("" if first else " ") + remaining[:size])
        remaining = remaining[size:]
        first = False
        limit = 74
    parts.append(("" if first else " ") + remaining)
    return "\r\n".join(parts)


def event_uid(match: Match) -> str:
    # Datum und Uhrzeit absichtlich nicht in der ID: Terminänderungen aktualisieren
    # vorhandene Kalendereinträge, statt Dubletten anzulegen.
    stable = (
        f"{match.season_start_year}-{match.season_start_year + 1}|"
        f"{match.competition}|THW Kiel|{match.opponent}"
    )
    digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20]
    return f"{digest}@thw-heimspiele.local"


def build_ics(matches: list[Match]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//THW Kiel Heimspielkalender//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:THW Kiel Heimspiele",
        "X-WR-TIMEZONE:Europe/Berlin",
        "X-WR-CALDESC:Heimspiele des THW Kiel in der MERKUR Ostseehalle",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:PT24H",
        "BEGIN:VTIMEZONE",
        "TZID:Europe/Berlin",
        "X-LIC-LOCATION:Europe/Berlin",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "DTSTART:19700329T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0200",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "DTSTART:19701025T030000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for match in matches:
        summary = f"THW Kiel - {match.opponent}"
        if match.provisional:
            summary += " (Termin vorläufig)"
        season = f"{match.season_start_year}/{str(match.season_start_year + 1)[-2:]}"
        description = (
            f"{match.competition}\nSaison: {season}\nQuelle: {match.source_url}"
        )
        if match.result:
            description = (
                f"{match.competition}\nSaison: {season}\nErgebnis: {match.result}"
                f"\nQuelle: {match.source_url}"
            )

        lines.extend(["BEGIN:VEVENT", f"UID:{event_uid(match)}", f"DTSTAMP:{stamp}"])
        if match.time:
            start = datetime.combine(match.day, datetime.strptime(match.time, "%H:%M").time())
            end = start + timedelta(hours=2)
            lines.extend(
                [
                    f"DTSTART;TZID=Europe/Berlin:{start:%Y%m%dT%H%M%S}",
                    f"DTEND;TZID=Europe/Berlin:{end:%Y%m%dT%H%M%S}",
                ]
            )
        else:
            lines.extend(
                [
                    f"DTSTART;VALUE=DATE:{match.day:%Y%m%d}",
                    f"DTEND;VALUE=DATE:{match.day + timedelta(days=1):%Y%m%d}",
                    "TRANSP:TRANSPARENT",
                ]
            )
        lines.extend(
            [
                f"SUMMARY:{ics_escape(summary)}",
                f"LOCATION:{ics_escape(LOCATION)}",
                f"DESCRIPTION:{ics_escape(description)}",
                f"URL:{match.source_url}",
                "STATUS:TENTATIVE" if match.provisional else "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"


def main() -> None:
    active_year = current_season_start_year()
    matches: list[Match] = []
    loaded_seasons: list[int] = []

    # Neben der laufenden Saison wird die Folgesaison geprüft. Dadurch tauchen
    # früh veröffentlichte Termine bereits vor dem offiziellen Saisonwechsel auf.
    for year in (active_year, active_year + 1):
        url = source_url(year)
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        if response.status_code == 404 and year == active_year + 1:
            continue
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        season_matches = parse_matches(response.text, year, url)
        if season_matches:
            matches.extend(season_matches)
            loaded_seasons.append(year)

    current_matches = [m for m in matches if m.season_start_year == active_year]
    if len(current_matches) < 5:
        raise RuntimeError(
            f"Sicherheitsabbruch: nur {len(current_matches)} Heimspiele für "
            f"{active_year}/{active_year + 1} erkannt; möglicherweise ist der "
            "neue Plan noch nicht veröffentlicht oder die Quellseite wurde geändert."
        )
    matches.sort(key=lambda item: (item.day, item.time or "", item.opponent))
    OUTPUT.write_text(build_ics(matches), encoding="utf-8", newline="")
    confirmed = sum(not match.provisional for match in matches)
    seasons = ", ".join(f"{year}/{str(year + 1)[-2:]}" for year in loaded_seasons)
    print(
        f"{OUTPUT.name}: {len(matches)} Heimspiele ({confirmed} bestätigt), "
        f"Saison(en): {seasons}"
    )


if __name__ == "__main__":
    main()
