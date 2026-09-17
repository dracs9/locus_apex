import { ChevronDown, GitCompareArrows, Lightbulb, Pencil, SearchX } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useFavorites, useRecommendations, useToggleFavorite, useUniversityMap } from "@/api/hooks";
import type { Tier } from "@/api/types";
import { ReasonChip, TierBadge } from "@/components/ds/badges";
import { Card, PageHeader } from "@/components/ds/Card";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/ds/states";
import { UniversityCard } from "@/components/ds/UniversityCard";
import { useProfileEditor } from "@/components/profile/ProfileEditorSheet";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { cn } from "@/lib/utils";
import { useNetwork, useUi } from "@/store/ui";

const TIERS: Tier[] = ["dream", "target", "safety"];
const TIER_HINT: Record<Tier, string> = { dream: t.tiers.dreamHint, target: t.tiers.targetHint, safety: t.tiers.safetyHint };

export function Recommendations() {
  const navigate = useNavigate();
  const recs = useRecommendations();
  const favorites = useFavorites();
  const { map } = useUniversityMap();
  const toggleFavorite = useToggleFavorite();
  const openEditor = useProfileEditor((s) => s.setOpen);
  const offline = useNetwork((s) => s.offline);
  const { compareIds, toggleCompare } = useUi();
  const [whyNotOpen, setWhyNotOpen] = useState(false);

  const favSet = new Set(favorites.data ?? []);
  const data = recs.data;

  return (
    <div>
      <PageHeader
        title={t.recs.title}
        subtitle={data ? t.recs.subtitle(data.recs.length) : undefined}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => openEditor(true)} disabled={offline}>
              <Pencil /> {t.recs.editProfile}
            </Button>
            <Button size="sm" onClick={() => navigate("/compare")} disabled={compareIds.length < 2}>
              <GitCompareArrows /> {t.recs.compareSelected(compareIds.length)}
            </Button>
          </>
        }
      />

      {recs.isPending && <CardsSkeleton count={4} />}
      {recs.isError && !data && <ErrorState onRetry={() => recs.refetch()} />}

      {data && (
        <div className="space-y-8">
          {data.suggestions.length > 0 && (
            <Card className="border-accent/40 bg-accent/5 p-4">
              <p className="mb-2 flex items-center gap-2 font-semibold">
                <Lightbulb className="h-4 w-4 text-accent" />
                {data.recs.length === 0 ? t.recs.noneTitle : t.recs.suggestionsTitle}
              </p>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {data.suggestions.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
              <Button variant="link" size="sm" onClick={() => openEditor(true)} className="mt-1">
                {t.recs.editProfile}
              </Button>
            </Card>
          )}

          {data.recs.length === 0 && data.suggestions.length === 0 && (
            <EmptyState icon={<SearchX className="h-6 w-6" />} title={t.recs.noneTitle} action={<Button onClick={() => openEditor(true)}>{t.recs.editProfile}</Button>} />
          )}

          {data.recs.length > 0 && compareIds.length < 2 && <p className="-mt-4 text-xs text-muted-foreground">{t.recs.selectToCompare}</p>}

          {data.recs.length > 0 &&
            TIERS.map((tier) => {
              const list = data.recs.filter((r) => r.tier === tier);
              return (
                <section key={tier} aria-labelledby={`tier-${tier}`}>
                  <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <h2 id={`tier-${tier}`} className="flex items-center gap-2 text-lg font-bold">
                      <TierBadge tier={tier} className="text-sm" />
                      <span className="text-muted-foreground">{list.length}</span>
                    </h2>
                    <p className="text-xs text-muted-foreground">{TIER_HINT[tier]}</p>
                  </div>
                  {list.length === 0 ? (
                    <p className="rounded-md border border-dashed px-4 py-3 text-sm text-muted-foreground">{t.recs.empty}</p>
                  ) : (
                    <div className="grid gap-3 lg:grid-cols-2">
                      {list.map((rec) => (
                        <UniversityCard
                          key={rec.university_id}
                          rec={rec}
                          uni={map.get(rec.university_id)}
                          favorite={favSet.has(rec.university_id)}
                          disabled={offline || toggleFavorite.isPending}
                          onFavorite={() => toggleFavorite.mutate({ id: rec.university_id, on: !favSet.has(rec.university_id) })}
                          selected={compareIds.includes(rec.university_id)}
                          onSelect={() => toggleCompare(rec.university_id)}
                        />
                      ))}
                    </div>
                  )}
                </section>
              );
            })}

          {data.excluded.length > 0 && (
            <Collapsible open={whyNotOpen} onOpenChange={setWhyNotOpen}>
              <CollapsibleTrigger asChild>
                <button type="button" className="flex w-full items-center justify-between rounded-lg border bg-card px-4 py-3 text-left font-semibold hover:bg-muted">
                  {t.recs.whyNot(data.excluded.length)}
                  <ChevronDown className={cn("h-4 w-4 transition-transform", whyNotOpen && "rotate-180")} />
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 space-y-2">
                {data.excluded.map((e) => (
                  <div key={e.university_id} className="rounded-md border bg-card px-4 py-3">
                    <Link to={`/university/${e.university_id}`} className="text-sm font-semibold hover:underline">
                      {map.get(e.university_id)?.name ?? e.university_id}
                    </Link>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {e.reasons.map((r) => (
                        <ReasonChip key={r.code} reason={r} />
                      ))}
                    </div>
                  </div>
                ))}
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
      )}
    </div>
  );
}
