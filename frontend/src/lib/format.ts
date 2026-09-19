import { t } from "@/i18n/ru";

export function money(v: number | null | undefined): string {
  if (v == null) return t.common.notPublished;
  return "$" + Math.round(v).toLocaleString("ru-RU").replace(/ | /g, " ");
}

/** Acceptance rate as "about 1 in N" — the app never shows percentages. */
export function oneIn(rate: number | null | undefined): string {
  if (rate == null) return t.common.notPublished;
  if (rate <= 0) return "почти никого";
  const n = Math.round(1 / rate);
  return n <= 1 ? "почти всех" : `≈1 из ${n}`;
}

const MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
const MONTHS_FULL = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];

/** Parses 'YYYY-MM-DD' as a local date (no timezone shift). */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toIsoDate(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function shortDate(iso: string): string {
  const d = parseDate(iso);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function monthKey(iso: string): string {
  return iso.slice(0, 7);
}

export function monthTitle(key: string): string {
  const [y, m] = key.split("-").map(Number);
  return `${MONTHS_FULL[m - 1]} ${y}`;
}

export function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((parseDate(toIso).getTime() - parseDate(fromIso).getTime()) / 86_400_000);
}

export function todayIso(): string {
  return toIsoDate(new Date());
}

/** GPA 5 -> 4 (same table as backend engine/config.py), for display only. */
export function gpa5to4(gpa5: number): number {
  const table: [number, number][] = [[2.0, 1.0], [3.0, 2.0], [3.5, 2.5], [4.0, 3.0], [4.5, 3.5], [5.0, 4.0]];
  if (gpa5 <= table[0][0]) return table[0][1];
  for (let i = 1; i < table.length; i++) {
    const [x0, y0] = table[i - 1];
    const [x1, y1] = table[i];
    if (gpa5 <= x1) return Math.round((y0 + ((gpa5 - x0) * (y1 - y0)) / (x1 - x0)) * 100) / 100;
  }
  return 4.0;
}

/** Intake year from grade: a student in grade G starts university after finishing grade 12. */
export function intakeYearFor(grade: number, now = new Date()): number {
  const schoolYearStart = now.getMonth() >= 6 ? now.getFullYear() : now.getFullYear() - 1;
  return schoolYearStart + (12 - grade) + 1;
}

export function pluralRu(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function countryName(code: string): string {
  return t.countries[code] ?? code;
}

/** Countries present in the catalog: US first, then by number of universities, then by name. */
export function catalogCountries(unis: { country: string }[]): string[] {
  const counts = new Map<string, number>();
  for (const u of unis) counts.set(u.country, (counts.get(u.country) ?? 0) + 1);
  return [...counts.keys()].sort(
    (a, b) =>
      Number(b === "US") - Number(a === "US") ||
      counts.get(b)! - counts.get(a)! ||
      countryName(a).localeCompare(countryName(b), "ru"),
  );
}

type DiffLike = { added: string[]; removed: string[]; tier_changed: unknown[]; chance_changed: unknown[] };

/** "+2, −1, ↕1" summary for the toast. */
export function diffSummary(diff: DiffLike): string | null {
  const parts: string[] = [];
  if (diff.added.length) parts.push(`+${diff.added.length}`);
  if (diff.removed.length) parts.push(`−${diff.removed.length}`);
  const moved = diff.tier_changed.length + diff.chance_changed.length;
  if (moved) parts.push(`↕${moved}`);
  return parts.length ? parts.join(", ") : null;
}

/** Same rule as backend engine/normalize.project_deadline: shift a seed deadline to the student's intake cycle. */
export function projectDeadline(iso: string, intakeYear: number): string {
  const d = parseDate(iso);
  const dataIntake = d.getMonth() >= 7 ? d.getFullYear() + 1 : d.getFullYear();
  const shifted = new Date(d.getFullYear() + (intakeYear - dataIntake), d.getMonth(), Math.min(d.getDate(), d.getMonth() === 1 ? 28 : d.getDate()));
  return toIsoDate(shifted);
}
