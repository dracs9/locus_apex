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
export function suggestedMajors(answers: Answers, available: string[]) {
  if (!complete(answers)) return [];
  const scores = Object.fromEntries(
    interestScores(answers).map((s) => [s.code, s.score]),
  );
  const all = Object.values(scores);
  if (Math.max(...all) === Math.min(...all)) return []; // No arbitrary career result for a flat profile.
  return Object.entries(data.major_codes)
    .filter(([id]) => available.includes(id))
    .map(([id, codes]) => ({
      id,
      score: codes.reduce((n, code) => n + scores[code], 0) / codes.length,
    }))
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
    .slice(0, 3)
    .map((m) => m.id);
}
export function hollandCode(answers: Answers) {
  const scores = interestScores(answers).sort((a, b) => b.score - a.score);
  if (!complete(answers) || scores[0].score === scores[5].score) return null;
  return scores
    .slice(0, 3)
    .map((s) => s.code)
    .join("");
}
