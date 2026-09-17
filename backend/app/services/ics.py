"""Minimal RFC 5545 calendar export of roadmap steps (all-day events)."""
from datetime import datetime, timedelta, timezone

from app.schemas import Roadmap


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """Lines longer than 75 octets are folded with a leading space."""
    out, current = [], ""
    for ch in line:
        if len((current + ch).encode()) > 73:
            out.append(current)
            current = " " + ch
        else:
            current += ch
    out.append(current)
    return out


def roadmap_to_ics(roadmap: Roadmap) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Admission Route//RU", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:Маршрут поступления"]
    for s in roadmap.steps:
        desc = "Выполнено" if s.done else "Не выполнено"
        if s.source_url:
            desc += f"\nИсточник: {s.source_url}"
        if s.is_demo:
            desc += "\nДемо-данные: проверьте дату на сайте вуза"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{s.id.replace(':', '-')}@admission-route",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{s.due_date:%Y%m%d}",
            f"DTEND;VALUE=DATE:{s.due_date + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_escape(('✓ ' if s.done else '') + s.title)}",
            f"DESCRIPTION:{_escape(desc)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(folded for line in lines for folded in _fold(line)) + "\r\n"
