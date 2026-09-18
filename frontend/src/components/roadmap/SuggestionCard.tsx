import { CalendarClock, Lightbulb, Loader2, Plus } from "lucide-react";

import type { Suggestion, University } from "@/api/types";
import { SourceBadge } from "@/components/ds/badges";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ui/button";
import { t } from "@/i18n/ru";
import { shortDate } from "@/lib/format";

export function SuggestionCard({
  suggestion: s,
  description,
  unis,
  onAdd,
  adding,
  disabled,
}: {
  suggestion: Suggestion;
  description?: string;
  unis: Map<string, University>;
  onAdd: () => void;
  adding: boolean;
  disabled: boolean;
}) {
  const names = s.university_ids.map((id) => unis.get(id)?.name ?? id);
  return (
    <Card className="flex flex-col gap-3 rounded-2xl p-4">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <span className="mb-1.5 inline-block rounded bg-muted px-1.5 py-0.5 text-xs font-semibold text-muted-foreground">
            {t.roadmap.kinds[s.kind]}
          </span>
          <h3 className="font-semibold leading-snug">{s.title}</h3>
        </div>
        <Button size="sm" onClick={onAdd} disabled={disabled || adding} className="shrink-0">
          {adding ? <Loader2 className="animate-spin" /> : <Plus />} {t.roadmap.addToPlan}
        </Button>
      </div>
      <p className="inline-flex items-start gap-1.5 self-start rounded-md bg-plus-soft px-2 py-1 text-xs font-medium text-plus">
        <Lightbulb className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />
        {s.why.text}
      </p>
      <p className="text-sm text-muted-foreground">{description ?? s.description}</p>
      <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <CalendarClock className="h-3.5 w-3.5" /> {t.roadmap.suggestedDate} {shortDate(s.suggested_due)}
        </span>
        {s.university_ids.length > 0 && <SourceBadge sourceUrl={s.source_url} isDemo={s.is_demo} />}
        {names.length > 0 && (
          <span className="truncate">
            {t.roadmap.forUnis} {names.join(" · ")}
          </span>
        )}
      </div>
    </Card>
  );
}
