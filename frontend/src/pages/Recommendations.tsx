import {
  ChevronDown,
  GitCompareArrows,
  Lightbulb,
  Pencil,
  SearchX,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  useFavorites,
  useRecommendations,
  useToggleFavorite,
  useUniversityMap,
} from "@/api/hooks";
import type { Tier } from "@/api/types";
import { ReasonChip } from "@/components/ds/badges";
import { Card, PageHeader } from "@/components/ds/Card";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/ds/states";
import { UniversityCard } from "@/components/ds/UniversityCard";
import { useProfileEditor } from "@/components/profile/ProfileEditorSheet";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { countryName } from "@/lib/format";
import { cn } from "@/lib/utils";
import { MAX_COMPARE, useNetwork, useUi } from "@/store/ui";

const TIERS: Tier[] = ["dream", "target", "safety"];
/** Cards shown per tier before "показать ещё". */
const PREVIEW_PER_TIER = 3;

export function Recommendations() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const country = params.get("country") ?? "all";
  const [tier, setTier] = useState<Tier | "all">("all");
  const recs = useRecommendations();
  const favorites = useFavorites();
  const { map } = useUniversityMap();
  const toggleFavorite = useToggleFavorite();
  const openEditor = useProfileEditor((s) => s.setOpen);
  const offline = useNetwork((s) => s.offline);
  const { compareIds, toggleCompare } = useUi();
  const [whyNotOpen, setWhyNotOpen] = useState(false);
  const [expanded, setExpanded] = useState<Partial<Record<Tier, boolean>>>({});

  const favSet = new Set(favorites.data ?? []);
  const data = recs.data;
  const countryOf = (id: string) => map.get(id)?.country ?? "unknown";
  const countries = [
    ...new Set([
      "US",
      "HK",
      "CN",
      "IT",
      ...Array.from(map.values()).map((u) => u.country),
    ]),
  ];
  const visible = (data?.recs ?? []).filter(
    (r) =>
      (country === "all" || countryOf(r.university_id) === country) &&
      (tier === "all" || r.tier === tier),
  );
  const sections = TIERS.filter((tr) => tier === "all" || tr === tier);
  const excluded = (data?.excluded ?? []).filter(
    (r) => country === "all" || countryOf(r.university_id) === country,
  );

  return (
    <div>
      <PageHeader
        title={t.recs.title}
        subtitle={data ? t.recs.subtitle(data.recs.length) : undefined}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openEditor(true)}
              disabled={offline}
            >
              <Pencil /> {t.recs.editProfile}
            </Button>
            <Button
              size="sm"
              onClick={() => navigate("/compare")}
              disabled={compareIds.length < 2}
            >
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
                {data.recs.length === 0
                  ? t.recs.noneTitle
                  : t.recs.suggestionsTitle}
              </p>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {data.suggestions.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
              <Button
                variant="link"
                size="sm"
                onClick={() => openEditor(true)}
                className="mt-1"
              >
                {t.recs.editProfile}
              </Button>
            </Card>
          )}

          {data.recs.length === 0 && data.suggestions.length === 0 && (
            <EmptyState
              icon={<SearchX className="h-6 w-6" />}
              title={t.recs.noneTitle}
              action={
                <Button onClick={() => openEditor(true)}>
                  {t.recs.editProfile}
                </Button>
              }
            />
          )}

          {data.recs.length > 0 && compareIds.length < 2 && (
            <p className="-mt-4 text-xs text-muted-foreground">
              {t.recs.selectToCompare}
            </p>
          )}

          <div className="space-y-3 rounded-xl border bg-card p-4">
            <p className="text-sm font-semibold">Университеты по странам</p>
            <div className="flex flex-wrap gap-2" aria-label="Фильтр по стране">
              {["all", ...countries].map((code) => (
                <Button
                  key={code}
                  size="sm"
                  variant={country === code ? "default" : "outline"}
                  aria-pressed={country === code}
                  onClick={() =>
                    setParams(code === "all" ? {} : { country: code })
                  }
                >
                  {code === "all" ? "Все страны" : countryName(code)}
                </Button>
              ))}
            </div>
            <div
              className="flex flex-wrap gap-2"
              aria-label="Сложность поступления"
            >
              {(["all", ...TIERS] as const).map((value) => (
                <Button
                  key={value}
                  size="sm"
                  variant={tier === value ? "secondary" : "ghost"}
                  aria-pressed={tier === value}
                  onClick={() => setTier(value)}
                >
                  {value === "all" ? "Все варианты" : t.tiers[value]}
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Подборка учитывает страны и направления из вашей анкеты. Фильтр
              помогает ориентироваться в результатах.
            </p>
          </div>
          {visible.length === 0 && (
            <Card className="p-5">
              <p className="font-semibold">В этой подборке пока нет вузов</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Проверьте выбранные страны в анкете и причины исключения ниже.
                Для некоторых стран каталог ещё пополняется.
              </p>
            </Card>
          )}
          {sections.map((tr) => {
            const inTier = visible.filter((r) => r.tier === tr);
            const open = expanded[tr] ?? false;
            const shown = open ? inTier : inTier.slice(0, PREVIEW_PER_TIER);
            const rest = inTier.length - shown.length;
            return (
              <section key={tr} aria-labelledby={`tier-${tr}`}>
                <div className="mb-4 flex items-center gap-3">
                  <h2 id={`tier-${tr}`} className="text-xl font-bold">
                    {t.tiers[tr]}
                  </h2>
                  <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                    {inTier.length}
                  </span>
                </div>
                {inTier.length === 0 ? (
                  <Card className="p-4 text-sm text-muted-foreground">
                    {t.recs.empty}
                  </Card>
                ) : (
                  <>
                    <div className="grid gap-4 lg:grid-cols-2">
                      {shown.map((rec) => (
                        <UniversityCard
                          key={rec.university_id}
                          rec={rec}
                          uni={map.get(rec.university_id)}
                          favorite={favSet.has(rec.university_id)}
                          disabled={offline || toggleFavorite.isPending}
                          onFavorite={() =>
                            toggleFavorite.mutate({
                              id: rec.university_id,
                              on: !favSet.has(rec.university_id),
                            })
                          }
                          selected={compareIds.includes(rec.university_id)}
                          onSelect={() => toggleCompare(rec.university_id)}
                          selectDisabled={
                            compareIds.length >= MAX_COMPARE &&
                            !compareIds.includes(rec.university_id)
                          }
                        />
                      ))}
                    </div>
                    {(rest > 0 || open) && inTier.length > PREVIEW_PER_TIER && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-3"
                        onClick={() =>
                          setExpanded((s) => ({ ...s, [tr]: !open }))
                        }
                        aria-expanded={open}
                      >
                        {open ? t.recs.showLess : t.recs.showMore(rest)}
                      </Button>
                    )}
                  </>
                )}
              </section>
            );
          })}

          {excluded.length > 0 && (
            <Collapsible open={whyNotOpen} onOpenChange={setWhyNotOpen}>
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex w-full items-center justify-between rounded-lg border bg-card px-4 py-3 text-left font-semibold hover:bg-muted"
                >
                  {t.recs.whyNot(excluded.length)}
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 transition-transform",
                      whyNotOpen && "rotate-180",
                    )}
                  />
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 space-y-2">
                {excluded.map((e) => (
                  <div
                    key={e.university_id}
                    className="rounded-md border bg-card px-4 py-3"
                  >
                    <Link
                      to={`/university/${e.university_id}`}
                      className="text-sm font-semibold hover:underline"
                    >
                      {map.get(e.university_id)?.name ?? e.university_id} ·{" "}
                      {countryName(countryOf(e.university_id))}
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
