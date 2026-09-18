import { AlertTriangle, CalendarPlus, ListPlus, Plus, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { downloadIcs, useAddStep, useRoadmap, useRoadmapText, useSuggestions, useUniversityMap } from "@/api/hooks";
import type { Suggestion } from "@/api/types";
import { GeneratedMark, Pill } from "@/components/ds/badges";
import { Card, PageHeader, SectionTitle } from "@/components/ds/Card";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/ds/states";
import { StepRow } from "@/components/ds/StepRow";
import { StepSheet, useStepSheet } from "@/components/roadmap/StepSheet";
import { SuggestionCard } from "@/components/roadmap/SuggestionCard";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { monthKey, monthTitle } from "@/lib/format";
import { filterSuggestions, type SuggestionFilter } from "@/lib/suggestions";
import { useNetwork } from "@/store/ui";

const MAX_TEXTS = 20; // per list, so one /ai/roadmap-text call stays within its 40-id limit

export function Roadmap() {
  const roadmap = useRoadmap();
  const suggestions = useSuggestions();
  const { map } = useUniversityMap();
  const add = useAddStep();
  const { openNew, openEdit } = useStepSheet();
  const offline = useNetwork((s) => s.offline);
  const [filter, setFilter] = useState<SuggestionFilter>("all");
  const [addingId, setAddingId] = useState<string | null>(null);

  const steps = roadmap.data?.steps ?? [];
  const all = suggestions.data ?? [];
  // the last suggestion of a category was just added: fall back to "all" instead of an empty list
  const active = filter === "all" || all.some((s) => s.kind === filter) ? filter : "all";
  const { counts, shown } = filterSuggestions(all, active);
  const texts = useRoadmapText([
    ...steps.filter((s) => !s.done).slice(0, MAX_TEXTS).map((s) => s.id),
    ...shown.slice(0, MAX_TEXTS).map((s) => s.id),
  ]);
  const descriptions = new Map((texts.data?.items ?? []).map((i) => [i.id, i.description]));

  const addSuggestion = async (s: Suggestion) => {
    setAddingId(s.id);
    try {
      const plan = await add.mutateAsync({ suggestion_id: s.id });
      const created = plan.steps.find((x) => x.source_key === s.id);
      toast.success(t.roadmap.added(s.title), {
        action: created ? { label: t.roadmap.changeDate, onClick: () => openEdit(created) } : undefined,
      });
    } catch {
      /* the mutation shows the error */
    } finally {
      setAddingId(null);
    }
  };

  if (roadmap.isPending) return <CardsSkeleton count={5} />;
  if (roadmap.isError && !roadmap.data) return <ErrorState onRetry={() => roadmap.refetch()} />;
  const data = roadmap.data!;
  const conflicts = new Map(data.conflicts.map((c) => [c.step_id, c.message]));
  const done = steps.filter((s) => s.done).length;
  const months = [...new Set(steps.map((s) => monthKey(s.due_date)))];

  return (
    <div className="space-y-8">
      <PageHeader
        title={t.roadmap.title}
        subtitle={t.roadmap.subtitle}
        actions={
          <>
            <Button size="sm" onClick={openNew} disabled={offline}>
              <Plus /> {t.roadmap.addOwn}
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/mentor">
                <Sparkles /> {t.mentor.ask}
              </Link>
            </Button>
            {steps.length > 0 && (
              <Button variant="outline" size="sm" onClick={() => void downloadIcs()}>
                <CalendarPlus /> {t.roadmap.exportIcs}
              </Button>
            )}
          </>
        }
      />

      <section className="space-y-5">
        {steps.length === 0 ? (
          <EmptyState icon={<ListPlus className="h-6 w-6" />} title={t.roadmap.empty} text={t.roadmap.emptyHint} />
        ) : (
          <>
            <Card className="space-y-3 p-4">
              <div className="flex items-center justify-between text-sm font-semibold">
                <span>{t.roadmap.progress(done, steps.length)}</span>
                {texts.data && <GeneratedMark generated={texts.data.generated} />}
              </div>
              <Progress value={data.progress} />
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
                  <SectionTitle className="sticky top-0 z-10 -mx-1 bg-background/95 px-1 py-1 capitalize backdrop-blur">
                    {monthTitle(m)}
                  </SectionTitle>
                  <ul className="space-y-2 border-l-2 border-dashed border-border pl-3">
                    {steps
                      .filter((s) => monthKey(s.due_date) === m)
                      .map((s) => (
                        <StepRow
                          key={s.id}
                          step={s}
                          description={descriptions.get(s.id)}
                          conflict={conflicts.get(s.id)}
                          unis={map}
                          onEdit={() => openEdit(s)}
                        />
                      ))}
                  </ul>
                </li>
              ))}
            </ol>
          </>
        )}
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-bold md:text-2xl">
            <Sparkles className="h-5 w-5 text-primary" /> {t.roadmap.suggestionsTitle}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">{t.roadmap.suggestionsHint}</p>
        </div>

        {suggestions.isPending ? (
          <CardsSkeleton count={3} />
        ) : suggestions.isError && !suggestions.data ? (
          <ErrorState onRetry={() => suggestions.refetch()} />
        ) : all.length === 0 ? (
          <EmptyState title={t.roadmap.suggestionsEmpty} />
        ) : (
          <>
            <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:px-0">
              <Pill active={active === "all"} onClick={() => setFilter("all")} className="shrink-0">
                {t.roadmap.suggestionsAll} <span className="opacity-70">{all.length}</span>
              </Pill>
              {counts.map((c) => (
                <Pill key={c.kind} active={active === c.kind} onClick={() => setFilter(c.kind)} className="shrink-0">
                  {t.roadmap.kindsShort[c.kind]} <span className="opacity-70">{c.count}</span>
                </Pill>
              ))}
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {shown.map((s) => (
                <SuggestionCard
                  key={s.id}
                  suggestion={s}
                  description={descriptions.get(s.id)}
                  unis={map}
                  onAdd={() => void addSuggestion(s)}
                  adding={addingId === s.id}
                  disabled={offline || addingId !== null}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <StepSheet />
    </div>
  );
}
