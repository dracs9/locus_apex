import { motion } from "framer-motion";
import { Loader2, Plus, Star, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useFavorites, usePreview, useProfile, useRecommendations, useToggleFavorite, useUniversityMap } from "@/api/hooks";
import type { Priorities, Recommendation } from "@/api/types";
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
import { useNetwork, useUi } from "@/store/ui";

const PRIORITY_KEYS = ["cost", "prestige", "aid", "location"] as const;

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
    const ids = [...new Set([...valid, ...favs, ...perTier, ...recIds])].slice(0, 3);
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
  const addable = (recs.data?.recs ?? []).filter((r) => !compareIds.includes(r.university_id)).slice(0, 8);

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
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {columns.map((rec, i) => {
            const uni = map.get(rec.university_id);
            const firstDeadline = uni?.deadlines.find((d) => d.value);
            return (
              <motion.div key={rec.university_id} layout transition={{ type: "spring", stiffness: 350, damping: 32 }}>
                <Card className={cn("flex h-full flex-col gap-3 p-4", i === 0 && "border-primary/50 ring-1 ring-primary/30")}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-primary">{t.compare.rank(i + 1)}</p>
                      <Link to={`/university/${rec.university_id}`} className="font-semibold leading-snug hover:underline">
                        {uni?.name ?? rec.university_id}
                      </Link>
                    </div>
                    <button type="button" onClick={() => toggleCompare(rec.university_id)} className="rounded-full p-1.5 text-muted-foreground hover:bg-muted" aria-label="Убрать из сравнения">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <TierBadge tier={rec.tier} />
                    <ChanceBadge chance={rec.chance} />
                  </div>
                  {uni && (
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                      <dt className="text-muted-foreground">{t.university.cost}</dt>
                      <dd className="font-semibold">{money(uni.cost_per_year_usd.value)}</dd>
                      <dt className="text-muted-foreground">{t.university.aid}</dt>
                      <dd className="font-semibold">{uni.intl_aid.value ? t.aid[uni.intl_aid.value] : t.common.notPublished}</dd>
                      <dt className="text-muted-foreground">{t.university.acceptance}</dt>
                      <dd className="font-semibold">{oneIn(uni.acceptance_rate.value)}</dd>
                      <dt className="text-muted-foreground">{t.university.ielts}</dt>
                      <dd className="font-semibold">{uni.ielts_min.value ?? t.common.notPublished}</dd>
                      <dt className="text-muted-foreground">{t.university.rank}</dt>
                      <dd className="font-semibold">#{uni.world_rank}</dd>
                      <dt className="text-muted-foreground">{t.university.deadlines}</dt>
                      <dd className="font-semibold">
                        {firstDeadline?.value && profile.data ? shortDate(projectDeadline(firstDeadline.value.date, profile.data.intake_year)) : t.common.notPublished}
                      </dd>
                    </dl>
                  )}
                  {uni && <SourceBadge isDemo={uni.cost_per_year_usd.is_demo} sourceUrl={uni.cost_per_year_usd.source_url} checkedAt={uni.cost_per_year_usd.checked_at} />}
                  <div className="flex flex-wrap gap-1.5">
                    {pickReasons(rec.reasons).map((r) => (
                      <ReasonChip key={r.code + r.text} reason={r} />
                    ))}
                  </div>
                  <div className="mt-auto pt-1">
                    <Button
                      className="w-full"
                      variant={favSet.has(rec.university_id) ? "outline" : "default"}
                      onClick={() => toggleFavorite.mutate({ id: rec.university_id, on: !favSet.has(rec.university_id) })}
                      disabled={offline || toggleFavorite.isPending}
                    >
                      <Star className={cn(favSet.has(rec.university_id) && "fill-accent text-accent")} />
                      {favSet.has(rec.university_id) ? t.university.inPlan : t.compare.pickFavorite}
                    </Button>
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}

      {compareIds.length < 3 && addable.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold">{t.compare.add}</p>
          <div className="flex flex-wrap gap-2">
            {addable.map((r) => (
              <Pill key={r.university_id} onClick={() => toggleCompare(r.university_id)} className="min-h-9 px-3 py-1.5 text-xs">
                <Plus className="h-3.5 w-3.5" />
                {map.get(r.university_id)?.name ?? r.university_id}
              </Pill>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
