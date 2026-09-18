import { describe, expect, it } from "vitest";

import type { Profile } from "@/api/types";

import { profileCompleteness } from "./profileCompleteness";

const base = {
  grade: 11,
  gpa5: null,
  academic_record: null,
  holland: null,
  majors: ["cs"],
  countries: ["US"],
  budget_per_year_usd: 30000,
  needs_aid: true,
  intake_year: 2027,
  priorities: { cost: 0.5, prestige: 0.5, location: 0.5, aid: 0.5 },
  achievements: [],
  created_at: "2026-09-01T00:00:00Z",
} as unknown as Profile;

const achievement = (type: string, status = "done") =>
  ({ id: type, type, status, score: 1, title: null, level: null, date: "2026-09-01" }) as unknown as Profile["achievements"][number];

describe("profileCompleteness", () => {
  it("is empty for a bare profile and lists everything missing", () => {
    const r = profileCompleteness(base, 0);
    expect(r.value).toBe(0);
    expect(r.missing).toHaveLength(8);
  });

  it("counts only done achievements", () => {
    const planned = { ...base, achievements: [achievement("SAT", "planned")] };
    expect(profileCompleteness(planned, 0).value).toBe(0);
    const done = { ...base, achievements: [achievement("SAT"), achievement("IELTS"), achievement("PROJECT")] };
    expect(profileCompleteness(done, 0).value).toBe(3 / 8);
  });

  it("reaches 100% with a full profile", () => {
    const full = {
      ...base,
      academic_record: { scale: "5", value: 4.8 },
      holland: { version: "applyra-riasec-v1", answers: {} },
      majors: ["cs", "math"],
      priorities: { ...base.priorities, cost: 0.8 },
      achievements: [achievement("SAT"), achievement("TOEFL"), achievement("OLYMPIAD")],
    } as unknown as Profile;
    expect(profileCompleteness(full, 3)).toEqual({ value: 1, missing: [] });
  });
});
