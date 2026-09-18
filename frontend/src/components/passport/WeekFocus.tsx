import { ArrowRight, Check } from "lucide-react";
import { Link } from "react-router-dom";

import type { RoadmapStep } from "@/api/types";
import { Card } from "@/components/ds/Card";
import { useCompleteStep } from "@/components/ds/StepRow";
import { t } from "@/i18n/ru";
import { daysBetween, shortDate, todayIso } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

/** The nearest open steps of the plan: earliest due date first, then priority. */
export function focusSteps(steps: RoadmapStep[], n = 3): RoadmapStep[] {
  return steps
    .filter((s) => !s.done)
    .sort((a, b) => a.due_date.localeCompare(b.due_date) || b.priority - a.priority || a.id.localeCompare(b.id))
    .slice(0, n);
}

export function WeekFocus({ steps }: { steps: RoadmapStep[] }) {
  const complete = useCompleteStep();
  const offline = useNetwork((s) => s.offline);
  const focus = focusSteps(steps);
  const done = steps.filter((s) => s.done).length;
  const today = todayIso();

  return (
    <Card className="rounded-2xl p-6">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-lg font-bold">{t.passport.weekFocus}</h2>
        <span className="rounded-lg bg-muted px-2.5 py-1 text-xs font-bold text-muted-foreground">
          {done}/{steps.length}
        </span>
      </div>
      {focus.length === 0 ? (
        <p className="py-4 text-sm text-muted-foreground">{steps.length ? t.passport.allDone : t.roadmap.empty}</p>
      ) : (
        <ul className="divide-y">
          {focus.map((s) => {
            const days = daysBetween(today, s.due_date);
            return (
              <li key={s.id} className="flex items-start gap-3 py-4">
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={s.done}
                  aria-label={s.title}
                  onClick={() => complete.toggle(s)}
                  disabled={offline || complete.isPending}
                  className={cn(
                    "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-colors hover:border-primary disabled:opacity-50",
                    s.done && "border-primary bg-primary text-primary-foreground",
                  )}
                >
                  {s.done && <Check className="h-3.5 w-3.5" />}
                </button>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold leading-snug">{s.title}</p>
                  <p className={cn("mt-1 text-sm text-muted-foreground", days < 0 && "text-blocker")}>
                    {t.roadmap.kinds[s.kind]} · {days < 0 ? t.roadmap.overdue : days <= 7 ? t.passport.thisWeek : `${t.roadmap.due} ${shortDate(s.due_date)}`}
                  </p>
                </div>
                <Link to="/roadmap" aria-label={t.passport.openPlan} className="mt-0.5 text-muted-foreground hover:text-foreground">
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
