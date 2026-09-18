import { describe, expect, it } from "vitest";

import type { Suggestion } from "@/api/types";

import { filterSuggestions } from "./suggestions";

const s = (id: string, kind: Suggestion["kind"]) => ({ id, kind }) as Suggestion;
const list = [s("exam:SAT", "exam"), s("act:hackathon", "activity"), s("act:volunteering", "activity")];

describe("filterSuggestions", () => {
  it("counts kinds in pill order and skips empty ones", () => {
    expect(filterSuggestions(list, "all").counts).toEqual([
      { kind: "activity", count: 2 },
      { kind: "exam", count: 1 },
    ]);
  });

  it("filters by kind and keeps the original order", () => {
    expect(filterSuggestions(list, "activity").shown.map((x) => x.id)).toEqual(["act:hackathon", "act:volunteering"]);
    expect(filterSuggestions(list, "all").shown).toHaveLength(3);
    expect(filterSuggestions(list, "document").shown).toEqual([]);
  });
});
