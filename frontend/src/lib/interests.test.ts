import { describe, expect, it } from "vitest";
import {
  complete,
  holland,
  hollandCode,
  interestScores,
  suggestedCareers,
  suggestedMajors,
} from "./interests";
import careers from "@/data/careers.json";
const answers = (v: number) =>
  Object.fromEntries(holland.questions.map((q) => [q.id, v]));
describe("Holland interests", () => {
  it("requires all answers and accepts zero", () => {
    expect(complete({})).toBe(false);
    expect(complete(answers(0))).toBe(true);
    expect(complete({ ...answers(2), R1: 5 })).toBe(false);
  });
  it("does not invent a career code from flat answers", () => {
    expect(hollandCode(answers(2))).toBeNull();
    expect(suggestedMajors(answers(2), ["cs", "design"])).toEqual([]);
    expect(suggestedCareers(answers(2))).toEqual([]);
  });
  it("recommends only available directions and ranks research interests", () => {
    const a = answers(0);
    holland.questions
      .filter((q) => q.dimension === "I")
      .forEach((q) => {
        a[q.id] = 4;
      });
    expect(interestScores(a).find((s) => s.code === "I")?.score).toBe(20);
    expect(suggestedMajors(a, ["math", "design"])).toEqual(["math", "design"]);
    expect(hollandCode(a)?.[0]).toBe("I");
  });
  it("suggests careers deterministically from the leading codes", () => {
    const a = answers(0);
    holland.questions
      .filter((q) => q.dimension === "I" || q.dimension === "R")
      .forEach((q) => {
        a[q.id] = 4;
      });
    const first = suggestedCareers(a);
    expect(first).toHaveLength(6);
    expect(suggestedCareers(a)).toEqual(first);
    expect(["engineering", "physics", "biology", "cs"]).toContain(first[0].major);
    expect(suggestedCareers(a, 2)).toEqual(first.slice(0, 2));
  });
  it("links every career to a known major", () => {
    for (const c of careers) {
      expect(Object.keys(holland.major_codes)).toContain(c.major);
      expect(c.codes.every((code) => code in holland.dimensions)).toBe(true);
    }
  });
});
