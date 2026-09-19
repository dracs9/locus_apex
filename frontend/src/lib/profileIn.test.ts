import { describe, expect, it } from "vitest";

import type { Profile } from "@/api/types";

import { profileToIn } from "./profileIn";

const profile = {
  grade: 11,
  gpa5: 4.6,
  academic_record: null,
  holland: null,
  majors: ["cs"],
  countries: ["US", "UK"],
  budget_per_year_usd: 50000,
  needs_aid: true,
  intake_year: 2028,
  priorities: { cost: 0.5, prestige: 0.5, location: 0.5, aid: 0.5 },
  achievements: [{ id: "a", type: "SAT", score: 1400, date: "2026-08-01", status: "done" }],
  created_at: "2026-09-01T00:00:00Z",
} as unknown as Profile;

describe("profileToIn", () => {
  it("keeps the profile, drops achievements and applies the patch", () => {
    const body = profileToIn(profile, { countries: [...profile.countries, "HK"] });
    expect(body.countries).toEqual(["US", "UK", "HK"]);
    expect(body.majors).toEqual(["cs"]);
    expect(body.initial_achievements).toEqual([]);
    expect(body).not.toHaveProperty("achievements");
    expect(body).not.toHaveProperty("created_at");
  });
});
