import { motion } from "framer-motion";
import { Check, MapPin, Star } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import type { Reason, Recommendation, University } from "@/api/types";
import { t } from "@/i18n/ru";
import { countryName, money } from "@/lib/format";
import { cn } from "@/lib/utils";

import { ChanceBadge, ReasonChip, TierBadge } from "./badges";

/** Top reasons for a compact card: the first plus, the first risk, then the rest in order. */
export function pickReasons(reasons: Reason[], n = 3): Reason[] {
  const firstPlus = reasons.find((r) => r.kind === "plus");
  const firstRisk = reasons.find((r) => r.kind !== "plus");
  const head = [firstPlus, firstRisk].filter((r): r is Reason => !!r);
  return [...head, ...reasons.filter((r) => !head.includes(r))].slice(0, n);
}

interface Props {
  rec: Recommendation;
  uni: University | undefined;
  favorite: boolean;
  onFavorite?: () => void;
  selected?: boolean;
  onSelect?: () => void;
  disabled?: boolean;
}

export function UniversityCard({ rec, uni, favorite, onFavorite, selected, onSelect, disabled }: Props) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? pickReasons(rec.reasons, rec.reasons.length) : pickReasons(rec.reasons);
  const hidden = rec.reasons.length - shown.length;

  return (
    <motion.article layout="position" transition={{ type: "spring", stiffness: 400, damping: 35 }} className="rounded-lg border bg-card p-4 shadow-[0_1px_2px_rgba(0,0,0,.04)]">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <Link to={`/university/${rec.university_id}`} className="block font-semibold leading-snug hover:text-primary hover:underline">
            {uni?.name ?? rec.university_id}
          </Link>
          {uni && (
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {uni.city}, {countryName(uni.country)}
              </span>
              <span>
                {money(uni.cost_per_year_usd.value)}
                {uni.cost_per_year_usd.value != null && t.common.perYear}
              </span>
            </p>
          )}
        </div>
        {onFavorite && (
          <button
            type="button"
            onClick={onFavorite}
            disabled={disabled}
            aria-pressed={favorite}
            aria-label={favorite ? t.recs.unfavorite : t.recs.favorite}
            className={cn(
              "flex h-9 shrink-0 items-center gap-1 rounded-full border px-3 text-xs font-bold transition-colors disabled:opacity-50",
              favorite ? "border-accent bg-accent/15 text-foreground" : "hover:bg-muted",
            )}
          >
            <Star className={cn("h-4 w-4", favorite && "fill-accent text-accent")} />
            <span className="hidden sm:inline">{favorite ? t.recs.unfavorite : t.recs.favorite}</span>
          </button>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <TierBadge tier={rec.tier} />
        <ChanceBadge chance={rec.chance} />
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {shown.map((r) => (
          <ReasonChip key={r.code + r.text} reason={r} />
        ))}
        {hidden > 0 && (
          <button type="button" onClick={() => setExpanded(true)} className="rounded-md px-2 py-1 text-xs font-semibold text-primary hover:bg-muted">
            {t.recs.moreReasons(hidden)}
          </button>
        )}
      </div>

      {onSelect && (
        <button
          type="button"
          onClick={onSelect}
          aria-pressed={selected}
          className={cn("mt-3 inline-flex items-center gap-2 text-xs font-semibold", selected ? "text-primary" : "text-muted-foreground hover:text-foreground")}
        >
          <span className={cn("flex h-4 w-4 items-center justify-center rounded border", selected && "border-primary bg-primary text-primary-foreground")}>
            {selected && <Check className="h-3 w-3" />}
          </span>
          {t.recs.compare}
        </button>
      )}
    </motion.article>
  );
}
