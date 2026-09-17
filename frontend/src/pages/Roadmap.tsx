import { AlertTriangle, CalendarPlus, Star } from "lucide-react";
import { Link } from "react-router-dom";

import { downloadIcs, useFavorites, useRoadmap, useRoadmapText, useUniversityMap } from "@/api/hooks";
import { GeneratedMark } from "@/components/ds/badges";
import { Card, PageHeader, SectionTitle } from "@/components/ds/Card";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/ds/states";
import { StepRow } from "@/components/ds/StepRow";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { monthKey, monthTitle } from "@/lib/format";

export function Roadmap() {
  const roadmap = useRoadmap();
  const favorites = useFavorites();
  const { map } = useUniversityMap();
  const steps = roadmap.data?.steps ?? [];
  const texts = useRoadmapText(steps.filter((s) => !s.done).slice(0, 40).map((s) => s.id));

  if (roadmap.isPending) return <CardsSkeleton count={5} />;
  if (roadmap.isError && !roadmap.data) return <ErrorState onRetry={() => roadmap.refetch()} />;
  const data = roadmap.data!;

  const descriptions = new Map((texts.data?.items ?? []).map((i) => [i.id, i.description]));
  const conflicts = new Map(data.conflicts.map((c) => [c.step_id, c.message]));
  const done = steps.filter((s) => s.done).length;
  const targets = [...new Set(steps.filter((s) => s.kind === "application").flatMap((s) => s.university_ids))];
  const months = [...new Set(steps.map((s) => monthKey(s.due_date)))];

  return (
    <div className="space-y-5">
      <PageHeader
        title={t.roadmap.title}
        subtitle={t.roadmap.subtitle}
        actions={
          steps.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => void downloadIcs()}>
              <CalendarPlus /> {t.roadmap.exportIcs}
            </Button>
          )
        }
      />

      {steps.length === 0 ? (
        <EmptyState title={t.roadmap.empty} action={<Button asChild><Link to="/recommendations">{t.nav.universities}</Link></Button>} />
      ) : (
        <>
          <Card className="space-y-3 p-4">
            <div className="flex items-center justify-between text-sm font-semibold">
              <span>{t.roadmap.progress(done, steps.length)}</span>
              {texts.data && <GeneratedMark generated={texts.data.generated} />}
            </div>
            <Progress value={data.progress} />
            <div className="text-sm">
              <span className="text-muted-foreground">{t.roadmap.basedOn} </span>
              {targets.map((id, i) => (
                <span key={id}>
                  {i > 0 && ", "}
                  <Link to={`/university/${id}`} className="font-semibold hover:underline">
                    {map.get(id)?.name ?? id}
                  </Link>
                </span>
              ))}
            </div>
            {(favorites.data ?? []).length === 0 && (
              <p className="flex items-start gap-2 text-xs text-muted-foreground">
                <Star className="mt-px h-3.5 w-3.5 shrink-0" /> {t.roadmap.fallbackNote}
              </p>
            )}
          </Card>

          {data.conflicts.length > 0 && (
            <Card className="border-blocker/40 bg-blocker-soft/40 p-4" role="alert">
              <p className="mb-2 flex items-center gap-2 font-semibold text-blocker">
                <AlertTriangle className="h-4 w-4" /> {t.roadmap.conflicts}: {data.conflicts.length}
              </p>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {data.conflicts.map((c) => (
                  <li key={c.step_id}>{c.message}</li>
                ))}
              </ul>
            </Card>
          )}

          <ol className="space-y-6">
            {months.map((m) => (
              <li key={m}>
                <SectionTitle className="sticky top-0 z-10 -mx-1 bg-background/95 px-1 py-1 capitalize backdrop-blur">{monthTitle(m)}</SectionTitle>
                <ul className="space-y-2 border-l-2 border-dashed border-border pl-3">
                  {steps
                    .filter((s) => monthKey(s.due_date) === m)
                    .map((s) => (
                      <StepRow key={s.id} step={s} description={descriptions.get(s.id)} conflict={conflicts.get(s.id)} unis={map} />
                    ))}
                </ul>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
