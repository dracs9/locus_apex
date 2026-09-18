import { HollandResult } from "@/components/interests/HollandQuiz";
import { ArrowRight, ChevronDown, HelpCircle, History, ListChecks, Pencil, Settings, ShieldAlert, Sparkles, Target } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  useFavorites,
  useMajors,
  usePassportText,
  useProfile,
  useRecommendations,
  useRoadmap,
  useToggleFavorite,
  useUniversityMap,
} from "@/api/hooks";
import type { PassportItem } from "@/api/types";
import { Card } from "@/components/ds/Card";
import { EmptyState, ErrorState } from "@/components/ds/states";
import { AdviceCard } from "@/components/passport/AdviceCard";
import { GoalHero } from "@/components/passport/GoalHero";
import { PassportUniCard } from "@/components/passport/PassportUniCard";
import { StatTiles } from "@/components/passport/StatTiles";
import { WeekFocus } from "@/components/passport/WeekFocus";
import { useProfileEditor } from "@/components/profile/ProfileEditorSheet";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { profileCompleteness } from "@/lib/profileCompleteness";
import { profileFieldAnswer } from "@/lib/profileFields";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

function Item({ item, answer, tone }: { item: PassportItem; answer: { label: string; value: string }; tone: "plus" | "risk" | "blocker" | "neutral" }) {
  const [open, setOpen] = useState(false);
  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={cn(
          "flex w-full items-start gap-2 rounded-md px-3 py-2.5 text-left text-sm font-medium transition-colors",
          tone === "plus" && "bg-plus-soft/60 hover:bg-plus-soft",
          tone === "risk" && "bg-risk-soft/60 hover:bg-risk-soft",
          tone === "blocker" && "bg-blocker-soft/60 hover:bg-blocker-soft",
          tone === "neutral" && "bg-muted/60 hover:bg-muted",
        )}
      >
        <span className="flex-1">{item.text}</span>
        <ChevronDown className={cn("mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <p className="px-3 pt-1.5 text-xs text-muted-foreground">
          {t.passport.sourceAnswer} <span className="font-semibold text-foreground">{answer.label}</span> — {answer.value}
        </p>
      )}
    </li>
  );
}

function Block({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <Card className="p-4">
      <h2 className="mb-3 flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-wide text-muted-foreground">
        {icon}
        {title}
      </h2>
      <ul className="space-y-2">{children}</ul>
    </Card>
  );
}

export function Passport() {
  const navigate = useNavigate();
  const profile = useProfile();
  const passport = usePassportText(!!profile.data);
  const recs = useRecommendations(!!profile.data);
  const roadmap = useRoadmap(!!profile.data);
  const favorites = useFavorites(!!profile.data);
  const toggleFavorite = useToggleFavorite();
  const majors = useMajors();
  const { map } = useUniversityMap();
  const openEditor = useProfileEditor((s) => s.setOpen);
  const offline = useNetwork((s) => s.offline);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const majorNames = new Map((majors.data ?? []).map((m) => [m.id, m.name_ru]));

  if (!profile.data) return null;
  const answer = (field: string) => profileFieldAnswer(profile.data, field, majorNames);

  const favIds = favorites.data ?? [];
  const favSet = new Set(favIds);
  const recList = recs.data?.recs ?? [];
  // The big goal: first saved university, else the top dream pick, else the top pick.
  const goalId = favIds[0] ?? recList.find((r) => r.tier === "dream")?.university_id ?? recList[0]?.university_id;
  const goal = goalId ? (map.get(goalId)?.name ?? goalId) : (passport.data?.goal.text ?? null);
  const steps = roadmap.data?.steps ?? [];
  const next = steps.find((s) => s.id === roadmap.data?.next_step_id);
  const completeness = profileCompleteness(profile.data, favIds.length);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">{t.passport.eyebrow}</p>
          <h1 className="mt-3 text-3xl font-bold leading-tight md:text-5xl">
            {t.passport.titleBefore}
            <em className="font-serif text-[1.06em] font-medium italic tracking-tight text-primary">{t.passport.titleAccent}</em>.
          </h1>
          <p className="mt-3 text-muted-foreground">{t.passport.subtitle}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => openEditor(true)}>
          <Pencil /> {t.passport.editProfile}
        </Button>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* Hero and stats come first on mobile; the side column follows them. */}
        <div className="min-w-0 space-y-5">
          <GoalHero profile={profile.data} goal={goal} nextStep={next?.title ?? null} completeness={completeness} />
          <StatTiles profile={profile.data} saved={favIds.length} done={steps.filter((s) => s.done).length} total={steps.length} />
        </div>

        <aside className="min-w-0 space-y-5 lg:row-span-2">
          {passport.isPending ? (
            <Skeleton className="h-64 rounded-2xl" />
          ) : passport.isError && !passport.data ? (
            <ErrorState onRetry={() => passport.refetch()} />
          ) : passport.data ? (
            <AdviceCard text={passport.data.risk.text} generated={passport.data.generated} />
          ) : null}
          {roadmap.isPending ? (
            <Skeleton className="h-72 rounded-2xl" />
          ) : roadmap.isError && !roadmap.data ? (
            <ErrorState onRetry={() => roadmap.refetch()} />
          ) : (
            <WeekFocus steps={steps} />
          )}
        </aside>

        <div className="min-w-0 space-y-5">
          <section>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 text-xl font-bold md:text-2xl">
                {t.passport.lookAt}
                <span title={t.passport.lookAtHelp} aria-label={t.passport.lookAtHelp} className="text-muted-foreground">
                  <HelpCircle className="h-4 w-4" />
                </span>
              </h2>
              <Link to="/recommendations" className="inline-flex items-center gap-1.5 font-bold text-primary hover:underline">
                {t.passport.allPicks} <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            {recs.isPending ? (
              <div className="space-y-4">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-48 rounded-2xl" />
                ))}
              </div>
            ) : recs.isError && !recs.data ? (
              <ErrorState onRetry={() => recs.refetch()} />
            ) : recList.length === 0 ? (
              <EmptyState title={t.recs.noneTitle} text={recs.data?.suggestions.join(" ")} />
            ) : (
              <div className="space-y-4">
                {recList.slice(0, 3).map((rec) => (
                  <PassportUniCard
                    key={rec.university_id}
                    rec={rec}
                    uni={map.get(rec.university_id)}
                    majorNames={majorNames}
                    saved={favSet.has(rec.university_id)}
                    disabled={offline || toggleFavorite.isPending}
                    onToggleSave={() => toggleFavorite.mutate({ id: rec.university_id, on: !favSet.has(rec.university_id) })}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="space-y-3">
            {profile.data.holland ? (
              <HollandResult answers={profile.data.holland.answers} />
            ) : (
              <Card className="p-5">
                <h2 className="font-bold">Начните с ваших интересов</h2>
                <p className="mt-2 text-sm text-muted-foreground">Тест Холланда поможет исследовать направления и уточнит подборку вузов.</p>
              </Card>
            )}
            <Button variant="outline" asChild>
              <Link to="/interests">{profile.data.holland ? "Пересмотреть интересы" : "Пройти тест Холланда"}</Link>
            </Button>
          </section>

          {passport.data && (
            <Card className="rounded-2xl">
              <button
                type="button"
                onClick={() => setDetailsOpen((o) => !o)}
                aria-expanded={detailsOpen}
                className="flex w-full items-center justify-between gap-2 p-5 text-left font-bold"
              >
                {t.passport.details}
                <ChevronDown className={cn("h-5 w-5 text-muted-foreground transition-transform", detailsOpen && "rotate-180")} />
              </button>
              {detailsOpen && (
                <div className="grid gap-3 px-5 pb-5 md:grid-cols-2">
                  <Block icon={<Sparkles className="h-4 w-4 text-plus" />} title={t.passport.strengths}>
                    {passport.data.strengths.map((s) => (
                      <Item key={s.text} item={s} answer={answer(s.profile_field)} tone="plus" />
                    ))}
                  </Block>
                  <Block icon={<Target className="h-4 w-4 text-muted-foreground" />} title={t.passport.constraints}>
                    {passport.data.constraints.map((s) => (
                      <Item key={s.text} item={s} answer={answer(s.profile_field)} tone="neutral" />
                    ))}
                  </Block>
                  <div className="md:col-span-2">
                    <Block icon={<ShieldAlert className="h-4 w-4 text-risk" />} title={t.passport.risk}>
                      <Item item={passport.data.risk} answer={answer(passport.data.risk.profile_field)} tone="risk" />
                    </Block>
                  </div>
                </div>
              )}
            </Card>
          )}

          <Button size="lg" className="w-full md:w-auto" onClick={() => navigate("/recommendations")}>
            {t.passport.showOptions} <ArrowRight />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 md:hidden">
        <Button variant="outline" asChild>
          <Link to="/history">
            <ListChecks /> {t.nav.achievements}
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/settings">
            <Settings /> {t.nav.settings}
          </Link>
        </Button>
        <Button variant="outline" asChild className="col-span-2">
          <Link to="/changes">
            <History /> {t.nav.changes}
          </Link>
        </Button>
      </div>
    </div>
  );
}
