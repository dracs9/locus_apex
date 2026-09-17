import { AlertTriangle, CheckCircle2, Circle } from "lucide-react";

import { usePatchStep } from "@/api/hooks";
import type { AchievementType, RoadmapStep, University } from "@/api/types";
import { useAchievementSheet } from "@/components/achievements/AddAchievementSheet";
import { t } from "@/i18n/ru";
import { daysBetween, shortDate, todayIso } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

import { SourceBadge } from "./badges";

export function examTypeOf(step: RoadmapStep): AchievementType | null {
  const m = /^exam:(SAT|IELTS|TOEFL)$/.exec(step.id);
  return m ? (m[1] as AchievementType) : null;
}

/** Marks a step done; finishing an exam step opens the achievement sheet prefilled with that exam (§8.7). */
export function useCompleteStep() {
  const patch = usePatchStep();
  const openNew = useAchievementSheet((s) => s.openNew);
  return {
    isPending: patch.isPending,
    toggle: (step: RoadmapStep) => {
      const done = !step.done;
      patch.mutate({ id: step.id, done });
      const exam = examTypeOf(step);
      if (done && exam) openNew(exam);
    },
  };
}

export function StepRow({
  step,
  description,
  conflict,
  unis,
}: {
  step: RoadmapStep;
  description?: string;
  conflict?: string;
  unis: Map<string, University>;
}) {
  const complete = useCompleteStep();
  const offline = useNetwork((s) => s.offline);
  const days = daysBetween(todayIso(), step.due_date);
  const names = step.university_ids.map((id) => unis.get(id)?.name ?? id);

  return (
    <li className={cn("flex gap-3 rounded-lg border bg-card p-3", conflict && !step.done && "border-blocker/50 bg-blocker-soft/30", step.done && "opacity-70")}>
      <button
        type="button"
        onClick={() => complete.toggle(step)}
        disabled={offline}
        aria-pressed={step.done}
        aria-label={step.done ? t.roadmap.markUndone : t.roadmap.markDone}
        className="mt-0.5 shrink-0 rounded-full text-primary disabled:opacity-50"
      >
        {step.done ? <CheckCircle2 className="h-6 w-6 fill-primary/15" /> : <Circle className="h-6 w-6 text-muted-foreground hover:text-primary" />}
      </button>
      <div className="min-w-0 flex-1 space-y-1">
        <p className={cn("font-semibold leading-snug", step.done && "line-through")}>{step.title}</p>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
          <span className="rounded bg-muted px-1.5 py-0.5 font-semibold">{t.roadmap.kinds[step.kind]}</span>
          <span className={cn(!step.done && days < 0 && "font-semibold text-blocker", !step.done && days >= 0 && days <= 14 && "font-semibold text-risk")}>
            {t.roadmap.due} {shortDate(step.due_date)} · {t.today.daysLeft(days)}
          </span>
          <SourceBadge sourceUrl={step.source_url} isDemo={step.is_demo} />
        </p>
        {description && !step.done && <p className="text-sm text-muted-foreground">{description}</p>}
        {names.length > 0 && <p className="truncate text-xs text-muted-foreground">{names.join(" · ")}</p>}
        {conflict && !step.done && (
          <p className="flex items-start gap-1.5 text-xs font-semibold text-blocker">
            <AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0" />
            {conflict}
          </p>
        )}
      </div>
    </li>
  );
}
