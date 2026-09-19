import type { EssaySummary } from "@/api/types";

export type EssayFilters = {
  q: string;
  level: string; // "" = all
  kind: string;
  major: string;
  university: string; // catalog id or school name
  mine: boolean;
  sort: "recommended" | "short" | "long";
};

export type EssayContext = { majors: string[]; favoriteIds: string[]; recIds: string[] };

/** Filter key for the university select: catalog id when the school is in the catalog, otherwise its name. */
export function universityKey(e: EssaySummary): string {
  return e.university_id ?? e.school ?? "";
}

/** Same weights as the backend's recommend_essays, so "most useful first" matches the recommendations. */
export function usefulness(e: EssaySummary, ctx: EssayContext): number {
  let score = e.level === "bachelor" ? 3 : 0;
  if (e.university_id && ctx.favoriteIds.includes(e.university_id)) score += 3;
  else if (e.university_id && ctx.recIds.includes(e.university_id)) score += 2;
  if (e.majors.some((m) => ctx.majors.includes(m))) score += 2;
  if (e.kind === "common_app" || e.kind === "personal_statement") score += 1;
  return score;
}

export function filterEssays(essays: EssaySummary[], f: EssayFilters, ctx: EssayContext): EssaySummary[] {
  const q = f.q.trim().toLowerCase();
  const mine = new Set([...ctx.favoriteIds, ...ctx.recIds]);
  const out = essays.filter(
    (e) =>
      (!f.level || e.level === f.level) &&
      (!f.kind || e.kind === f.kind) &&
      (!f.major || e.majors.includes(f.major)) &&
      (!f.university || universityKey(e) === f.university) &&
      (!f.mine || (e.university_id != null && mine.has(e.university_id))) &&
      (!q ||
        [e.school, e.program, e.author, e.excerpt, e.prompt, ...e.topics]
          .filter(Boolean)
          .some((s) => s!.toLowerCase().includes(q))),
  );
  const byId = (a: EssaySummary, b: EssaySummary) => a.id.localeCompare(b.id);
  if (f.sort === "short") return out.sort((a, b) => a.word_count - b.word_count || byId(a, b));
  if (f.sort === "long") return out.sort((a, b) => b.word_count - a.word_count || byId(a, b));
  return out.sort((a, b) => usefulness(b, ctx) - usefulness(a, ctx) || byId(a, b));
}
