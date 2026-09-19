import { BookOpen, Clock } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import type { EssaySummary } from "@/api/types";
import { ReasonChip } from "@/components/ds/badges";
import { Card } from "@/components/ds/Card";
import { t } from "@/i18n/ru";
import { cn } from "@/lib/utils";

export const WORDS_PER_MINUTE = 200;

export function readingMinutes(words: number): number {
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

export function LevelBadge({ level, className }: { level: EssaySummary["level"]; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold",
        level === "bachelor" ? "bg-safety-soft text-safety" : "bg-muted text-muted-foreground",
        className,
      )}
    >
      {t.essays.levels[level]}
    </span>
  );
}

export function LicenseBadge({ license }: { license: EssaySummary["license"] }) {
  return (
    <span className="text-[11px] text-muted-foreground">
      {license === "CC_BY_NC_SA_4_0" ? t.essays.licenseCc : t.essays.licenseUnknown}
    </span>
  );
}

/** One essay in a list: school, type, level, program, reading time and the first lines of the text. */
export function EssayCard({ essay, reasons }: { essay: EssaySummary; reasons?: string[] }) {
  const { search } = useLocation();
  return (
    <Card className="flex h-full flex-col p-4">
      <div className="flex flex-wrap items-center gap-2">
        <LevelBadge level={essay.level} />
        <span className="text-xs font-semibold text-muted-foreground">{t.essays.kinds[essay.kind]}</span>
      </div>
      <h3 className="mt-2 font-bold leading-snug">{essay.school ?? t.essays.levels.other}</h3>
      {(essay.topics.length > 0 || essay.program) && (
        <p className="mt-0.5 text-sm text-muted-foreground">
          {essay.topics.length ? essay.topics.join(" · ") : essay.program}
        </p>
      )}
      {reasons && reasons.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {reasons.map((r) => (
            <ReasonChip key={r} reason={{ kind: "plus", text: r }} />
          ))}
        </div>
      )}
      <p lang="en" className="mt-3 line-clamp-4 flex-1 text-sm leading-relaxed">
        {essay.excerpt}
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" aria-hidden />
          {t.essays.minutes(readingMinutes(essay.word_count))}
          {essay.author ? ` · ${essay.author}` : ""}
        </span>
        <Link
          to={`/essays/${essay.id}`}
          state={{ back: search }}
          className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline"
        >
          <BookOpen className="h-4 w-4" aria-hidden /> {t.essays.read}
        </Link>
      </div>
    </Card>
  );
}
