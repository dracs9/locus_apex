import { CalendarClock, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { useDeleteAchievement, useProfile } from "@/api/hooks";
import type { AchievementType } from "@/api/types";
import { useAchievementSheet } from "@/components/achievements/AddAchievementSheet";
import { AttachmentStrip } from "@/components/achievements/AttachmentStrip";
import { Pill } from "@/components/ds/badges";
import { PageHeader } from "@/components/ds/Card";
import { EmptyState } from "@/components/ds/states";
import { Button } from "@/components/ui/button";
import { t } from "@/i18n/ru";
import { shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

export function History() {
  const profile = useProfile();
  const del = useDeleteAchievement();
  const { openNew, openEdit } = useAchievementSheet();
  const offline = useNetwork((s) => s.offline);
  const [filter, setFilter] = useState<AchievementType | "ALL">("ALL");

  const all = [...(profile.data?.achievements ?? [])].sort((a, b) => b.date.localeCompare(a.date));
  const types = [...new Set(all.map((a) => a.type))];
  const list = filter === "ALL" ? all : all.filter((a) => a.type === filter);

  return (
    <div>
      <PageHeader
        title={t.achievements.title}
        actions={
          <Button size="sm" onClick={() => openNew()} disabled={offline}>
            <Plus /> {t.achievements.add}
          </Button>
        }
      />

      {all.length === 0 ? (
        <EmptyState title={t.achievements.empty} action={<Button onClick={() => openNew()} disabled={offline}>{t.achievements.add}</Button>} />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            <Pill active={filter === "ALL"} onClick={() => setFilter("ALL")} className="min-h-9 px-3 py-1.5 text-xs">
              {t.achievements.all}
            </Pill>
            {types.map((type) => (
              <Pill key={type} active={filter === type} onClick={() => setFilter(type)} className="min-h-9 px-3 py-1.5 text-xs">
                {t.achievements.types[type]}
              </Pill>
            ))}
          </div>

          <ol className="relative space-y-3 border-l-2 border-border pl-5">
            {list.map((a) => (
              <li key={a.id} className="relative">
                <span className={cn("absolute -left-[27px] top-4 h-3 w-3 rounded-full border-2 border-background", a.status === "done" ? "bg-primary" : "bg-muted-foreground/40")} aria-hidden />
                <div className="flex items-start gap-3 rounded-lg border bg-card p-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">
                      {t.achievements.types[a.type]}
                      {a.score != null && <span className="ml-2 font-display">{a.score}</span>}
                    </p>
                    {a.title && <p className="text-sm">{a.title}</p>}
                    <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <CalendarClock className="h-3 w-3" /> {shortDate(a.date)}
                      </span>
                      {a.level && <span>{t.achievements.levels[a.level]}</span>}
                      <span className={cn("rounded px-1.5 py-0.5 font-semibold", a.status === "planned" ? "bg-risk-soft text-risk" : "bg-plus-soft text-plus")}>
                        {a.status === "planned" ? t.achievements.planned : t.achievements.done}
                      </span>
                    </p>
                    <AttachmentStrip attachments={a.attachments} />
                  </div>
                  <Button size="icon" variant="ghost" onClick={() => openEdit(a)} disabled={offline} aria-label={t.common.edit}>
                    <Pencil />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    disabled={offline || del.isPending}
                    aria-label={t.common.delete}
                    onClick={() => {
                      if (window.confirm(t.achievements.confirmDelete)) del.mutate(a.id);
                    }}
                  >
                    <Trash2 className="text-blocker" />
                  </Button>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
