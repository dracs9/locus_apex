import { Loader2, Plus, Star, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useFavorites, usePreview, useProfile, useRecommendations, useToggleFavorite, useUniversityMap } from "@/api/hooks";
import type { Priorities, Recommendation, University } from "@/api/types";
import { ChanceBadge, Pill, ReasonChip, SourceBadge, TierBadge } from "@/components/ds/badges";
import { Card, PageHeader } from "@/components/ds/Card";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/ds/states";
import { pickReasons } from "@/components/ds/UniversityCard";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { t } from "@/i18n/ru";
import { money, oneIn, projectDeadline, shortDate } from "@/lib/format";
import { useDebounced } from "@/lib/useDebounced";
import { cn } from "@/lib/utils";
import { DEFAULT_COMPARE, MAX_COMPARE, useNetwork, useUi } from "@/store/ui";

const PRIORITY_KEYS = ["cost", "prestige", "aid", "location"] as const;

/** Fixed column widths keep ~6 universities on screen instead of one per viewport. */
const LABEL_W = 168;
const COL_W = 208;

/** Sticky label column + one cell per university. */
function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <tr>
      <th scope="row" className="sticky left-0 z-10 border-t border-border/60 bg-card py-3.5 pl-4 pr-3 text-left align-top text-sm font-semibold text-muted-foreground">
        {label}
      </th>
      {children}
    </tr>
  );
}

export function Compare() {
  const profile = useProfile();
  const recs = useRecommendations();
  const favorites = useFavorites();
  const toggleFavorite = useToggleFavorite();
  const { map } = useUniversityMap();
  const offline = useNetwork((s) => s.offline);
  const { compareIds, setCompare, toggleCompare } = useUi();
  const [priorities, setPriorities] = useState<Priorities | null>(null);

  useEffect(() => {
    if (profile.data && !priorities) setPriorities(profile.data.priorities);
  }, [profile.data, priorities]);

  // Default selection: favorites, then the best of each tier.
  useEffect(() => {
    if (!recs.data) return;
    const recIds = recs.data.recs.map((r) => r.university_id);
    const valid = compareIds.filter((id) => recIds.includes(id));
    if (valid.length >= 2) {
      if (valid.length !== compareIds.length) setCompare(valid);
      return;
    }
    const favs = (favorites.data ?? []).filter((id) => recIds.includes(id));
    const perTier = (["dream", "target", "safety"] as const)
      .map((tier) => recs.data.recs.find((r) => r.tier === tier)?.university_id)
      .filter((x): x is string => !!x);
    const ids = [...new Set([...valid, ...favs, ...perTier, ...recIds])].slice(0, DEFAULT_COMPARE);
    if (ids.length >= 2 && ids.join() !== compareIds.join()) setCompare(ids);
  }, [recs.data, favorites.data, compareIds, setCompare]);

  const debounced = useDebounced(priorities, 300);
  const preview = usePreview(profile.data, debounced);

  if (recs.isPending || profile.isPending) return <CardsSkeleton />;
  if (recs.isError && !recs.data) return <ErrorState onRetry={() => recs.refetch()} />;

  const source = preview.data ?? recs.data;
  const favSet = new Set(favorites.data ?? []);
  const columns = compareIds
    .map((id) => source?.recs.find((r) => r.university_id === id))
    .filter((r): r is Recommendation => !!r)
    .sort((a, b) => b.score - a.score || a.university_id.localeCompare(b.university_id));
  const addable = (recs.data?.recs ?? []).filter((r) => !compareIds.includes(r.university_id)).slice(0, 12);
  const full = compareIds.length >= MAX_COMPARE;

  /** One <td> per column, highlighting the best-ranked one. */
  const cells = (render: (rec: Recommendation, uni: University | undefined) => ReactNode) =>
    columns.map((rec, i) => (
      <td key={rec.university_id} className={cn("border-t border-border/60 px-4 py-3.5 align-top", i === 0 && "bg-primary/5")}>
        {render(rec, map.get(rec.university_id))}
      </td>
    ));

  return (
    <div className="space-y-5">
      <PageHeader title={t.compare.title} subtitle={t.compare.hint} />

      {priorities && (
        <Card className="grid gap-x-6 gap-y-3 p-4 sm:grid-cols-2">
          {PRIORITY_KEYS.map((k) => (
            <div key={k}>
              <div className="flex justify-between text-sm font-semibold">
                <span>{t.priorities[k]}</span>
                <span className="text-muted-foreground">{Math.round(priorities[k] * 10)}/10</span>
              </div>
              <Slider aria-label={t.priorities[k]} min={0} max={1} step={0.1} value={[priorities[k]]} onValueChange={([v]) => setPriorities({ ...priorities, [k]: v })} />
            </div>
          ))}
          <p className="flex items-center gap-2 text-xs text-muted-foreground sm:col-span-2">
            {preview.isFetching && <Loader2 className="h-3 w-3 animate-spin" />}
            Сохранённый профиль не меняется
          </p>
        </Card>
      )}

      {columns.length < 2 ? (
        <EmptyState title={t.compare.empty} action={<Button asChild><Link to="/recommendations">{t.nav.universities}</Link></Button>} />
      ) : (
        <Card className="p-0">
          <div className="overflow-x-auto rounded-xl">
            <table
              className="table-fixed border-separate border-spacing-0 text-base"
              style={{ width: LABEL_W + columns.length * COL_W }}
            >
              <caption className="sr-only">{t.compare.title}</caption>
              <colgroup>
                <col style={{ width: LABEL_W }} />
                {columns.map((rec) => (
                  <col key={rec.university_id} style={{ width: COL_W }} />
                ))}
              </colgroup>
              <thead>
                <tr>
                  <th scope="col" className="sticky left-0 z-20 bg-card py-3.5 pl-4 pr-3 text-left align-bottom text-sm font-semibold text-muted-foreground">
                    {t.compare.param}
                  </th>
                  {columns.map((rec, i) => {
                    const uni = map.get(rec.university_id);
                    return (
                      <th key={rec.university_id} scope="col" className={cn("px-4 py-3.5 text-left align-top", i === 0 && "bg-primary/5")}>
                        <div className="flex items-start justify-between gap-1">
                          <p className="text-xs font-bold text-primary">{t.compare.rank(i + 1)}</p>
                          <button type="button" onClick={() => toggleCompare(rec.university_id)} className="-mr-1 -mt-1 shrink-0 rounded-full p-1 text-muted-foreground hover:bg-muted" aria-label={t.compare.remove}>
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                        <Link to={`/university/${rec.university_id}`} className="mt-0.5 block font-semibold leading-snug hover:underline">
                          {uni?.name ?? rec.university_id}
                        </Link>
                        {uni && <p className="mt-0.5 text-sm font-normal text-muted-foreground">{uni.city}</p>}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                <Row label={t.compare.tier}>{cells((rec) => <TierBadge tier={rec.tier} className="text-sm" />)}</Row>
                <Row label={t.compare.chance}>{cells((rec) => <ChanceBadge chance={rec.chance} className="text-sm" />)}</Row>
                <Row label={t.university.cost}>{cells((_, uni) => <span className="font-semibold">{money(uni?.cost_per_year_usd.value ?? null)}</span>)}</Row>
                <Row label={t.university.aid}>
                  {cells((_, uni) => <span className="font-semibold">{uni?.intl_aid.value ? t.aid[uni.intl_aid.value] : t.common.notPublished}</span>)}
                </Row>
                <Row label={t.university.acceptance}>{cells((_, uni) => <span className="font-semibold">{oneIn(uni?.acceptance_rate.value ?? null)}</span>)}</Row>
                <Row label={t.university.sat}>
                  {cells((_, uni) => (
                    <span className="font-semibold">{uni?.sat.value ? `${uni.sat.value.p25}–${uni.sat.value.p75}` : t.common.notPublished}</span>
                  ))}
                </Row>
                <Row label={t.university.ielts}>{cells((_, uni) => <span className="font-semibold">{uni?.ielts_min.value ?? t.common.notPublished}</span>)}</Row>
                <Row label={t.university.rank}>{cells((_, uni) => <span className="font-semibold">{uni ? `#${uni.world_rank}` : t.common.notPublished}</span>)}</Row>
                <Row label={t.university.deadlines}>
                  {cells((_, uni) => {
                    const first = uni?.deadlines.find((d) => d.value);
                    return (
                      <span className="font-semibold">
                        {first?.value && profile.data ? shortDate(projectDeadline(first.value.date, profile.data.intake_year)) : t.common.notPublished}
                      </span>
                    );
                  })}
                </Row>
                <Row label={t.compare.source}>
                  {cells((_, uni) =>
                    uni ? <SourceBadge isDemo={uni.cost_per_year_usd.is_demo} sourceUrl={uni.cost_per_year_usd.source_url} checkedAt={uni.cost_per_year_usd.checked_at} /> : null,
                  )}
                </Row>
                <Row label={t.university.whyTitle}>
                  {cells((rec) => (
                    <div className="flex flex-wrap gap-1.5">
                      {pickReasons(rec.reasons, 2).map((r) => (
                        <ReasonChip key={r.code + r.text} reason={r} className="text-sm" />
                      ))}
                    </div>
                  ))}
                </Row>
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row" className="sticky left-0 z-10 border-t border-border/60 bg-card" />
                  {columns.map((rec, i) => (
                    <td key={rec.university_id} className={cn("border-t border-border/60 px-4 py-4 align-top", i === 0 && "bg-primary/5")}>
                      <Button
                        className="w-full"
                        size="sm"
                        variant={favSet.has(rec.university_id) ? "outline" : "default"}
                        onClick={() => toggleFavorite.mutate({ id: rec.university_id, on: !favSet.has(rec.university_id) })}
                        disabled={offline || toggleFavorite.isPending}
                      >
                        <Star className={cn(favSet.has(rec.university_id) && "fill-accent text-accent")} />
                        {favSet.has(rec.university_id) ? t.university.inPlan : t.compare.pickFavorite}
                      </Button>
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        </Card>
      )}

      {full ? (
        <p className="text-sm text-muted-foreground">{t.compare.limitReached}</p>
      ) : (
        addable.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-semibold">
              {t.compare.add} <span className="font-normal text-muted-foreground">({compareIds.length} / {MAX_COMPARE})</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {addable.map((r) => (
                <Pill key={r.university_id} onClick={() => toggleCompare(r.university_id)} className="min-h-9 px-3 py-1.5 text-xs">
                  <Plus className="h-3.5 w-3.5" />
                  {map.get(r.university_id)?.name ?? r.university_id}
                </Pill>
              ))}
            </div>
          </div>
        )
      )}
    </div>
  );
}
