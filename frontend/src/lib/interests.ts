import careers from "@/data/careers.json";
import data from "@/data/holland.json";

export type Dimension = keyof typeof data.dimensions;
export type Answers = Record<string, number>;
export const holland = data;
export const dimensions = Object.keys(data.dimensions) as Dimension[];
export const complete = (answers: Answers) =>
  data.questions.every(
    (q) =>
      Number.isInteger(answers[q.id]) &&
      answers[q.id] >= 0 &&
      answers[q.id] <= 4,
  );
export function interestScores(answers: Answers) {
  return dimensions.map((code) => ({
    code,
    label: data.dimensions[code],
    score: data.questions
      .filter((q) => q.dimension === code)
      .reduce((sum, q) => sum + (answers[q.id] ?? 0), 0),
  }));
}
/** Ranks items by the average score of their RIASEC codes; empty for incomplete or flat answers. */
function rankByCodes<T extends { id: string; codes: string[] }>(
  answers: Answers,
  items: T[],
): T[] {
  if (!complete(answers)) return [];
  const scores: Record<string, number> = Object.fromEntries(
    interestScores(answers).map((s) => [s.code, s.score]),
  );
  const all = Object.values(scores);
  if (Math.max(...all) === Math.min(...all)) return []; // No arbitrary career result for a flat profile.
  const avg = (codes: string[]) =>
    codes.reduce((n, code) => n + scores[code], 0) / codes.length;
  return [...items].sort(
    (a, b) => avg(b.codes) - avg(a.codes) || a.id.localeCompare(b.id),
  );
}
export function suggestedMajors(answers: Answers, available: string[]) {
  const majors = Object.entries(data.major_codes)
    .filter(([id]) => available.includes(id))
    .map(([id, codes]) => ({ id, codes }));
  return rankByCodes(answers, majors)
    .slice(0, 3)
    .map((m) => m.id);
}
export type Career = (typeof careers)[number];
export function suggestedCareers(answers: Answers, limit = 6): Career[] {
  return rankByCodes(answers, careers).slice(0, limit);
}
export function hollandCode(answers: Answers) {
  const scores = interestScores(answers).sort((a, b) => b.score - a.score);
  if (!complete(answers) || scores[0].score === scores[5].score) return null;
  return scores
    .slice(0, 3)
    .map((s) => s.code)
    .join("");
}
