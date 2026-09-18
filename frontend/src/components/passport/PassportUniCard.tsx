import { ArrowRight, Bookmark } from "lucide-react";
import { Link } from "react-router-dom";

import type { Recommendation, University } from "@/api/types";
import { ReasonChip } from "@/components/ds/badges";
import { Card } from "@/components/ds/Card";
import { pickReasons } from "@/components/ds/UniversityCard";
import { t } from "@/i18n/ru";
import { countryName } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Short mark for the logo tile: an abbreviation in parentheses, else initials, else the first letters. */
export function uniInitials(name: string): string {
  const abbr = /\(([A-Z]{2,6})\)/.exec(name)?.[1];
  if (abbr) return abbr;
  const words = name.split(/[\s-]+/).filter((w) => /^[A-ZА-Я]/.test(w) && !["University", "of", "The"].includes(w));
  if (words.length >= 2) return words.map((w) => w[0]).join("").slice(0, 5);
  return (words[0] ?? name).slice(0, 3).toUpperCase();
}

export function PassportUniCard({
  rec,
  uni,
  majorNames,
  saved,
  onToggleSave,
  disabled,
}: {
  rec: Recommendation;
  uni: University | undefined;
  majorNames: Map<string, string>;
  saved: boolean;
  onToggleSave: () => void;
  disabled?: boolean;
}) {
  const name = uni?.name ?? rec.university_id;
  const unverified = !uni || [uni.acceptance_rate, uni.sat, uni.ielts_min, ...uni.deadlines].some((f) => f.is_demo);
  const majors = (uni?.majors ?? []).slice(0, 3).map((m) => majorNames.get(m) ?? m);

  return (
    <Card className="rounded-2xl p-5 md:p-6">
      <div className="flex items-start gap-3">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border bg-muted/40 font-[Georgia,serif] text-sm font-bold text-foreground">
          {uniInitials(name)}
        </div>
        <div className="min-w-0 flex-1">
          <Link to={`/university/${rec.university_id}`} className="block font-bold leading-snug hover:text-primary md:text-lg">
            {name}
          </Link>
          {uni && (
            <p className="text-sm text-muted-foreground">
              {uni.city}, {countryName(uni.country)}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onToggleSave}
          disabled={disabled}
          aria-pressed={saved}
          aria-label={saved ? t.passport.unsave : t.passport.save}
          className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
        >
          <Bookmark className={cn("h-5 w-5", saved && "fill-primary text-primary")} />
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {pickReasons(rec.reasons, 2).map((r) => (
          <ReasonChip key={r.code + r.text} reason={r} />
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-end justify-between gap-3 border-t pt-4">
        <div className="min-w-0 text-sm">
          {majors.length > 0 && <p className="text-muted-foreground">{majors.join(" · ")}</p>}
          <p className="text-muted-foreground/80">{unverified ? t.passport.unverified : t.passport.verified}</p>
        </div>
        <Link
          to={`/university/${rec.university_id}`}
          className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline"
        >
          {t.passport.more} <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
}
