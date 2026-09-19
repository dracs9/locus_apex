import { describe, expect, it } from "vitest";

import { daysBetween, diffSummary, gpa5to4, intakeYearFor, money, oneIn, pluralRu, rank, shortDate } from "./format";

describe("format", () => {
  it("formats money without decimals", () => {
    expect(money(50000)).toBe("$50 000");
    expect(money(null)).toBe("не опубликовано");
  });

  it("shows unranked universities without a fake number", () => {
    expect(rank(42)).toBe("#42");
    expect(rank(1000)).toBe("нет в рейтинге QS");
  });

  it("never renders percentages for acceptance rates", () => {
    expect(oneIn(0.045)).toBe("≈1 из 22");
    expect(oneIn(0.9)).toBe("почти всех");
    expect(oneIn(0.25)).not.toContain("%");
  });

  it("converts GPA like the backend table", () => {
    expect(gpa5to4(5)).toBe(4);
    expect(gpa5to4(4.5)).toBe(3.5);
    expect(gpa5to4(4.25)).toBe(3.25);
  });

  it("computes intake year from grade", () => {
    const sept2026 = new Date(2026, 8, 17);
    expect(intakeYearFor(11, sept2026)).toBe(2028);
    expect(intakeYearFor(12, sept2026)).toBe(2027);
    expect(intakeYearFor(12, new Date(2027, 1, 1))).toBe(2027);
  });

  it("handles dates without timezone shifts", () => {
    expect(shortDate("2027-01-05")).toBe("5 янв 2027");
    expect(daysBetween("2026-09-17", "2026-10-01")).toBe(14);
  });

  it("summarizes a diff", () => {
    expect(diffSummary({ added: ["a", "b"], removed: [], tier_changed: [{}], chance_changed: [] })).toBe("+2, ↕1");
    expect(diffSummary({ added: [], removed: [], tier_changed: [], chance_changed: [] })).toBeNull();
  });

  it("pluralizes in Russian", () => {
    expect(pluralRu(1, "вуз", "вуза", "вузов")).toBe("вуз");
    expect(pluralRu(3, "вуз", "вуза", "вузов")).toBe("вуза");
    expect(pluralRu(11, "вуз", "вуза", "вузов")).toBe("вузов");
  });
});

describe("projectDeadline", () => {
  it("shifts deadlines to the intake cycle like the backend", async () => {
    const { projectDeadline } = await import("./format");
    expect(projectDeadline("2027-01-15", 2028)).toBe("2028-01-15");
    expect(projectDeadline("2026-11-01", 2027)).toBe("2026-11-01");
    expect(projectDeadline("2026-11-01", 2029)).toBe("2028-11-01");
    expect(projectDeadline("2027-07-15", 2027)).toBe("2027-07-15");
  });
});
