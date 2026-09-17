import { AlertTriangle, Ban, CheckCircle2, ExternalLink, FlaskConical, Sparkles, Star, Target, Shield, FileText } from "lucide-react";
import type { ReactNode } from "react";

import type { Chance, Reason, Tier } from "@/api/types";
import { t } from "@/i18n/ru";
import { shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const TIER_STYLE: Record<Tier, string> = {
  dream: "bg-dream-soft text-dream",
  target: "bg-target-soft text-target",
  safety: "bg-safety-soft text-safety",
};
const TIER_ICON: Record<Tier, typeof Star> = { dream: Star, target: Target, safety: Shield };

export function TierBadge({ tier, className }: { tier: Tier; className?: string }) {
  const Icon = TIER_ICON[tier];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold", TIER_STYLE[tier], className)}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {t.tiers[tier]}
    </span>
  );
}

/** Chance as a 3-segment meter + label. Never a percentage. */
export function ChanceBadge({ chance, className }: { chance: Chance; className?: string }) {
  const filled = { low: 1, medium: 2, high: 3 }[chance];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground", className)}>
      <span className="flex gap-0.5" aria-hidden>
        {[1, 2, 3].map((i) => (
          <span key={i} className={cn("h-2.5 w-1.5 rounded-sm", i <= filled ? "bg-foreground/70" : "bg-muted")} />
        ))}
      </span>
      {t.chance[chance]}
    </span>
  );
}

const REASON_STYLE: Record<Reason["kind"], string> = {
  plus: "bg-plus-soft text-plus",
  risk: "bg-risk-soft text-risk",
  blocker: "bg-blocker-soft text-blocker",
};
const REASON_ICON = { plus: CheckCircle2, risk: AlertTriangle, blocker: Ban };

export function ReasonChip({ reason, className }: { reason: Pick<Reason, "kind" | "text">; className?: string }) {
  const Icon = REASON_ICON[reason.kind];
  return (
    <span className={cn("inline-flex items-start gap-1.5 rounded-md px-2 py-1 text-xs font-medium leading-snug", REASON_STYLE[reason.kind], className)}>
      <Icon className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{reason.text}</span>
    </span>
  );
}

export function DemoBadge({ className }: { className?: string }) {
  return (
    <span
      title="Значение не проверено человеком по источнику — уточните на сайте вуза"
      className={cn("inline-flex items-center gap-1 rounded-full border border-dashed border-risk/50 px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide text-risk", className)}
    >
      <FlaskConical className="h-3 w-3" aria-hidden />
      {t.common.demoData}
    </span>
  );
}

/** Shows either a link to the verified source or the demo-data badge. */
export function SourceBadge({
  sourceUrl,
  checkedAt,
  isDemo,
  className,
}: {
  sourceUrl?: string | null;
  checkedAt?: string | null;
  isDemo: boolean;
  className?: string;
}) {
  if (isDemo) return <DemoBadge className={className} />;
  if (!sourceUrl) return null;
  return (
    <a
      href={sourceUrl}
      target="_blank"
      rel="noreferrer"
      className={cn("inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline", className)}
    >
      <FileText className="h-3 w-3" aria-hidden />
      {t.common.source}
      {checkedAt ? ` · ${t.common.checked} ${shortDate(checkedAt)}` : ""}
      <ExternalLink className="h-3 w-3" aria-hidden />
    </a>
  );
}

export function GeneratedMark({ generated }: { generated: boolean }) {
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
      {generated ? <Sparkles className="h-3 w-3" aria-hidden /> : <FileText className="h-3 w-3" aria-hidden />}
      {generated ? t.common.aiText : t.common.templateText}
    </span>
  );
}

export function Pill({ children, active, onClick, className }: { children: ReactNode; active?: boolean; onClick?: () => void; className?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex min-h-10 items-center gap-1.5 rounded-full border px-4 py-2 text-sm font-semibold transition-colors",
        active ? "border-primary bg-primary text-primary-foreground" : "border-input bg-card hover:bg-muted",
        className,
      )}
    >
      {children}
    </button>
  );
}
