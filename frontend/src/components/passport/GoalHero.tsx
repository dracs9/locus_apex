import { ArrowRight, HelpCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import type { Profile } from "@/api/types";
import { ProgressRing } from "@/components/ds/Card";
import { Button } from "@/components/ui/button";
import { t } from "@/i18n/ru";
import { countryName, money } from "@/lib/format";

export function GoalHero({
  profile,
  goal,
  nextStep,
  completeness,
}: {
  profile: Profile;
  goal: string | null;
  nextStep: string | null;
  completeness: { value: number; missing: string[] };
}) {
  const [help, setHelp] = useState(false);
  const pct = Math.round(completeness.value * 100);
  const money_ = profile.needs_aid
    ? t.passport.needsAid
    : `${money(profile.budget_per_year_usd)} ${t.passport.perYear}`;

  return (
    <section className="rounded-2xl border border-primary/20 bg-primary/5 p-5 md:p-8">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary/80">{t.passport.bigGoal}</p>
          <h2 className="mt-3 break-words text-3xl font-bold leading-tight md:text-4xl">{goal ?? "—"}</h2>
          <p className="mt-4 text-sm text-muted-foreground md:text-base">
            {profile.countries.map(countryName).join(" · ")} / {money_}
          </p>
          {nextStep && (
            <p className="mt-1 text-sm text-muted-foreground md:text-base">
              {t.passport.now} {nextStep}
            </p>
          )}
          <Button size="lg" className="mt-6" asChild>
            <Link to="/today">
              {t.passport.doNextStep} <ArrowRight />
            </Link>
          </Button>
        </div>

        <div className="flex shrink-0 flex-col items-center gap-2">
          <ProgressRing
            value={completeness.value}
            size={156}
            stroke={10}
            label={
              <>
                {pct}
                <span className="text-lg">%</span>
              </>
            }
            sublabel={t.passport.completeness}
          />
          <button
            type="button"
            onClick={() => setHelp((h) => !h)}
            aria-expanded={help}
            className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold text-muted-foreground hover:bg-muted"
          >
            <HelpCircle className="h-3.5 w-3.5" /> {t.passport.completenessHelp}
          </button>
        </div>
      </div>

      {help && (
        <div className="mt-5 rounded-xl border bg-card p-4 text-sm">
          {completeness.missing.length ? (
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              {completeness.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground">{t.passport.completenessFull}</p>
          )}
        </div>
      )}
    </section>
  );
}
