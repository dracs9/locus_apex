import { ArrowRight, CalendarClock, CheckCircle2, PartyPopper, Plus } from "lucide-react";
import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";

import { useChanceHistory, useProfile, useRoadmap, useRoadmapText, useUniversityMap } from "@/api/hooks";
import { useAchievementSheet } from "@/components/achievements/AddAchievementSheet";
import { SourceBadge } from "@/components/ds/badges";
import { Card, PageHeader, ProgressRing, SectionTitle } from "@/components/ds/Card";
import { EmptyState, ErrorState } from "@/components/ds/states";
import { useCompleteStep } from "@/components/ds/StepRow";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { daysBetween, shortDate, todayIso } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

const ChanceChart = lazy(() => import("@/components/ds/ChanceChart").then((m) => ({ default: m.ChanceChart })));

export function Today() {
  const profile = useProfile();
  const roadmap = useRoadmap();
  const history = useChanceHistory();
  const { map } = useUniversityMap();
  const openNew = useAchievementSheet((s) => s.openNew);
  const complete = useCompleteStep();
  const offline = useNetwork((s) => s.offline);
  const next = roadmap.data?.steps.find((s) => s.id === roadmap.data?.next_step_id);
  const text = useRoadmapText(next ? [next.id] : []);

  const steps = roadmap.data?.steps ?? [];
  const done = steps.filter((s) => s.done).length;
  const days = next ? daysBetween(todayIso(), next.due_date) : 0;
  const conflict = next ? roadmap.data?.conflicts.find((c) => c.step_id === next.id) : undefined;
  const hasHistory = (history.data?.length ?? 0) > 1;

  return (
    <div className="space-y-5">
      <PageHeader title={t.today.title} />

      {roadmap.isPending ? (
        <Skeleton className="h-52" />
      ) : roadmap.isError && !roadmap.data ? (
        <ErrorState onRetry={() => roadmap.refetch()} />
      ) : next ? (
        <Card className="relative overflow-hidden border-primary/30 p-5 md:p-6">
          <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-accent/10 blur-2xl" aria-hidden />
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-primary">{t.today.nextStep}</p>
          <h2 className="text-xl font-bold leading-snug md:text-2xl">{next.title}</h2>
          <p className={cn("mt-2 flex flex-wrap items-center gap-2 text-sm", days <= 14 ? "font-semibold text-risk" : "text-muted-foreground")}>
            <CalendarClock className="h-4 w-4" />
            {t.roadmap.due} {shortDate(next.due_date)} · {t.today.daysLeft(days)}
            <SourceBadge sourceUrl={next.source_url} isDemo={next.is_demo} />
          </p>
          {text.data?.items[0] && <p className="mt-3 text-sm text-muted-foreground">{text.data.items[0].description}</p>}
          {next.university_ids.length > 0 && (
            <p className="mt-2 text-xs text-muted-foreground">{next.university_ids.map((id) => map.get(id)?.name ?? id).join(" · ")}</p>
          )}
          {conflict && <p className="mt-2 text-xs font-semibold text-blocker">{conflict.message}</p>}
          <div className="mt-5 flex flex-wrap gap-2">
            <Button size="lg" onClick={() => complete.toggle(next)} disabled={offline || complete.isPending}>
              <CheckCircle2 /> {t.today.done}
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/roadmap">
                {t.today.goToPlan} <ArrowRight />
              </Link>
            </Button>
          </div>
        </Card>
      ) : (
        <EmptyState
          icon={<PartyPopper className="h-6 w-6" />}
          title={steps.length ? t.today.allDone : t.roadmap.empty}
          text={steps.length ? undefined : t.roadmap.emptyHint}
          action={
            steps.length ? undefined : (
              <Button asChild>
                <Link to="/roadmap">{t.roadmap.buildPlan}</Link>
              </Button>
            )
          }
        />
      )}

      <div className="grid gap-3 md:grid-cols-[220px_1fr]">
        <Card className="flex flex-row items-center gap-4 p-4 md:flex-col md:justify-center">
          <ProgressRing value={steps.length ? done / steps.length : 0} label={`${done}/${steps.length}`} />
          <div className="md:text-center">
            <p className="font-semibold">{t.today.progress}</p>
            <p className="text-sm text-muted-foreground">{t.roadmap.progress(done, steps.length)}</p>
          </div>
        </Card>

        <Card className="p-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <SectionTitle className="mb-0">{t.today.historyTitle}</SectionTitle>
            <Button size="sm" variant="accent" onClick={() => openNew()} disabled={offline}>
              <Plus /> {t.today.addAchievement}
            </Button>
          </div>
          {history.isPending ? (
            <Skeleton className="h-64" />
          ) : history.isError && !history.data ? (
            <ErrorState onRetry={() => history.refetch()} />
          ) : hasHistory && profile.data ? (
            <Suspense fallback={<Skeleton className="h-64" />}>
              <ChanceChart points={history.data!} unis={map} achievements={profile.data.achievements} />
            </Suspense>
          ) : (
            <p className="py-10 text-center text-sm text-muted-foreground">{t.today.historyEmpty}</p>
          )}
        </Card>
      </div>
    </div>
  );
}
