import { describe, expect, it } from "vitest";

import type { EssaySummary } from "@/api/types";

import { filterEssays, type EssayFilters } from "./essays";

const essay = (over: Partial<EssaySummary>): EssaySummary => ({
  id: "x",
  school: "MIT",
  university_id: "mit",
  level: "phd",
  kind: "statement_of_purpose",
  prompt: null,
  program: "Phd, NLP",
  majors: ["cs"],
  topics: ["NLP"],
  author: "A",
  license: "CC_BY_NC_SA_4_0",
  source_url: "https://openessays.org/essays/x",
  original_url: null,
  word_count: 1000,
  excerpt: "I study language models",
  ...over,
});

const none: EssayFilters = { q: "", level: "", kind: "", major: "", university: "", mine: false, sort: "recommended" };
const ctx = { majors: ["biology"], favoriteIds: ["yale"], recIds: [] };

const list = [
  essay({ id: "a" }),
  essay({ id: "b", level: "bachelor", kind: "common_app", school: "Yale University", university_id: "yale", word_count: 600 }),
  essay({ id: "c", level: "bachelor", kind: "common_app", school: "St. Olaf College", university_id: null, majors: ["biology"], word_count: 500 }),
];

describe("filterEssays", () => {
  it("puts bachelor essays for my universities and majors first", () => {
    expect(filterEssays(list, none, ctx).map((e) => e.id)).toEqual(["b", "c", "a"]);
  });

  it("filters by level, school without catalog id and my universities", () => {
    expect(filterEssays(list, { ...none, level: "phd" }, ctx).map((e) => e.id)).toEqual(["a"]);
    expect(filterEssays(list, { ...none, university: "St. Olaf College" }, ctx).map((e) => e.id)).toEqual(["c"]);
    expect(filterEssays(list, { ...none, mine: true }, ctx).map((e) => e.id)).toEqual(["b"]);
  });

  it("searches case-insensitively and sorts by length", () => {
    expect(filterEssays(list, { ...none, q: "LANGUAGE" }, ctx).map((e) => e.id)).toEqual(["b", "c", "a"]);
    expect(filterEssays(list, { ...none, q: "olaf" }, ctx).map((e) => e.id)).toEqual(["c"]);
    expect(filterEssays(list, { ...none, sort: "short" }, ctx).map((e) => e.id)).toEqual(["c", "b", "a"]);
  });
});
