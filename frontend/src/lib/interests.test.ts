import { describe, expect, it } from "vitest";
import {
  complete,
  holland,
  hollandCode,
  interestScores,
  suggestedMajors,
} from "./interests";
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
});
