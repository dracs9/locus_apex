import { Search, SearchX, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useEssays, useFavorites, useMajors, useProfile, useRecommendations, useRecommendedEssays } from "@/api/hooks";
import type { EssaySummary } from "@/api/types";
import { Card, PageHeader, SectionTitle } from "@/components/ds/Card";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/ds/states";
import { EssayCard } from "@/components/essays/EssayCard";
import { Button } from "@/components/ui/button";
import { Input, Switch } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { filterEssays, universityKey, type EssayFilters } from "@/lib/essays";

const LEVELS = ["bachelor", "master", "phd", "mba"] as const;
const KINDS = ["common_app", "personal_statement", "statement_of_purpose"] as const;
const SORTS = ["recommended", "short", "long"] as const;
const PAGE = 24;

function FilterRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label={label}>
      <span className="w-full text-xs font-semibold text-muted-foreground sm:w-28">{label}</span>
      {[{ value: "", label: t.essays.all }, ...options].map((o) => (
        <Button
          key={o.value || "all"}
          size="sm"
          variant={value === o.value ? "default" : "outline"}
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </Button>
      ))}
    </div>
  );
}

function universityOptions(essays: EssaySummary[]) {
  const counts = new Map<string, { label: string; n: number }>();
  for (const e of essays) {
    const key = universityKey(e);
    if (!key) continue;
    const cur = counts.get(key);
    counts.set(key, { label: e.school ?? key, n: (cur?.n ?? 0) + 1 });
  }
  return [...counts.entries()]
    .map(([value, { label, n }]) => ({ value, label: `${label} (${n})` }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export function Essays() {
  const [params, setParams] = useSearchParams();
  const essays = useEssays();
  const recommended = useRecommendedEssays();
  const majors = useMajors();
  const profile = useProfile();
  const favorites = useFavorites();
  const recs = useRecommendations();

  const filters: EssayFilters = {
    q: params.get("q") ?? "",
    level: params.get("level") ?? "",
    kind: params.get("kind") ?? "",
    major: params.get("major") ?? "",
    university: params.get("university") ?? "",
    mine: params.get("mine") === "1",
    sort: (SORTS as readonly string[]).includes(params.get("sort") ?? "")
      ? (params.get("sort") as EssayFilters["sort"])
      : "recommended",
  };
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };
  // Show the list in pages; any filter change starts from the first page again.
  const [page, setPage] = useState({ key: params.toString(), limit: PAGE });
  const limit = page.key === params.toString() ? page.limit : PAGE;
  const anyFilter = ["q", "level", "kind", "major", "university", "mine"].some((k) => params.get(k));

  const ctx = {
    majors: profile.data?.majors ?? [],
    favoriteIds: favorites.data ?? [],
    recIds: (recs.data?.recs ?? []).map((r) => r.university_id),
  };
  const all = essays.data ?? [];
  const visible = filterEssays(all, filters, ctx);
  const uniOptions = useMemo(() => universityOptions(essays.data ?? []), [essays.data]);
  const majorOptions = (majors.data ?? [])
    .filter((m) => all.some((e) => e.majors.includes(m.id)))
    .map((m) => ({ value: m.id, label: m.name_ru }));

  return (
    <div className="space-y-6">
      <PageHeader title={t.essays.title} subtitle={essays.data ? t.essays.subtitle(essays.data.length) : undefined} />

      {!anyFilter && (recommended.isPending || (recommended.data?.length ?? 0) > 0) && (
        <section>
          <SectionTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent" /> {t.essays.recommendedTitle}
          </SectionTitle>
          <p className="-mt-2 mb-3 text-sm text-muted-foreground">{t.essays.recommendedHint}</p>
          {recommended.isPending ? (
            <CardsSkeleton count={3} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {recommended.data!.map((r, i) => (
                // phones get the top 3, so the filters stay within reach
                <div key={r.essay.id} className={i >= 3 ? "hidden sm:block" : undefined}>
                  <EssayCard essay={r.essay} reasons={r.reasons} />
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <Card className="space-y-3 p-4">
        <label className="relative block">
          <span className="sr-only">{t.essays.search}</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            value={filters.q}
            onChange={(e) => set("q", e.target.value)}
            placeholder={t.essays.search}
            className="pl-9"
          />
        </label>
        <FilterRow
          label={t.essays.level}
          value={filters.level}
          options={LEVELS.map((l) => ({ value: l, label: t.essays.levels[l] }))}
          onChange={(v) => set("level", v)}
        />
        <FilterRow
          label={t.essays.kind}
          value={filters.kind}
          options={KINDS.map((k) => ({ value: k, label: t.essays.kinds[k] }))}
          onChange={(v) => set("kind", v)}
        />
        <FilterRow label={t.essays.major} value={filters.major} options={majorOptions} onChange={(v) => set("major", v)} />
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-muted-foreground">{t.essays.university}</span>
            <select
              value={filters.university}
              onChange={(e) => set("university", e.target.value)}
              className="h-10 w-full min-w-0 rounded-md border border-input bg-card px-3 text-sm"
            >
              <option value="">{t.essays.allUniversities}</option>
              {uniOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-muted-foreground">{t.essays.sort}</span>
            <select
              value={filters.sort}
              onChange={(e) => set("sort", e.target.value === "recommended" ? "" : e.target.value)}
              className="h-10 w-full min-w-0 rounded-md border border-input bg-card px-3 text-sm"
            >
              {SORTS.map((s) => (
                <option key={s} value={s}>
                  {t.essays.sorts[s]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm font-semibold">
            <Switch checked={filters.mine} onCheckedChange={(on) => set("mine", on ? "1" : "")} />
            {t.essays.myUniversities}
          </label>
          {anyFilter && (
            <Button variant="link" size="sm" onClick={() => setParams({}, { replace: true })}>
              {t.essays.reset}
            </Button>
          )}
        </div>
      </Card>

      {essays.isPending && <CardsSkeleton count={4} />}
      {essays.isError && !essays.data && <ErrorState onRetry={() => essays.refetch()} />}
      {essays.data && (
        <section>
          <p className="mb-3 text-sm text-muted-foreground">{t.essays.found(visible.length)}</p>
          {visible.length === 0 ? (
            <EmptyState
              icon={<SearchX className="h-6 w-6" />}
              title={t.essays.emptyTitle}
              text={t.essays.emptyText}
              action={<Button onClick={() => setParams({}, { replace: true })}>{t.essays.reset}</Button>}
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {visible.slice(0, limit).map((e) => (
                <EssayCard key={e.id} essay={e} />
              ))}
            </div>
          )}
          {visible.length > limit && (
            <div className="mt-4 flex justify-center">
              <Button variant="outline" onClick={() => setPage({ key: params.toString(), limit: limit + PAGE })}>
                {t.essays.showMore(Math.min(PAGE, visible.length - limit))}
              </Button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
