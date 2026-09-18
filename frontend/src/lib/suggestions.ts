import type { StepKind, Suggestion } from "@/api/types";

export type SuggestionFilter = StepKind | "all";

/** Order of the filter pills: what a student usually starts with first. */
export const FILTER_ORDER: StepKind[] = ["activity", "exam", "document", "application", "academic"];

/** Counts per kind (only kinds that occur, in FILTER_ORDER) and the suggestions matching the filter. */
export function filterSuggestions(list: Suggestion[], filter: SuggestionFilter) {
  const counts = FILTER_ORDER.map((kind) => ({ kind, count: list.filter((s) => s.kind === kind).length })).filter(
    (c) => c.count > 0,
  );
  const shown = filter === "all" ? list : list.filter((s) => s.kind === filter);
  return { counts, shown };
}
