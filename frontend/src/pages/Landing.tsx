import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useLoadDemo, useProfile } from "@/api/hooks";
import type { Tier } from "@/api/types";
import { ReasonChip, TierBadge } from "@/components/ds/badges";
import { Card } from "@/components/ds/Card";
import { NetworkBanners } from "@/components/ds/states";
import { Button } from "@/components/ui/button";
import { t } from "@/i18n/ru";

export function Landing() {
  const navigate = useNavigate();
  const profile = useProfile();
  const demo = useLoadDemo();
  const hasProfile = !!profile.data;

  const tryDemo = async () => {
    await demo.mutateAsync(undefined);
    navigate("/passport");
  };

  return (
    <div className="min-h-dvh">
      <NetworkBanners />
      <div className="mx-auto flex max-w-5xl flex-col gap-12 px-4 pb-16 pt-6 md:px-8 md:pt-10">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="h-5 w-5" />
            </span>
            <span className="font-display text-lg font-bold">{t.app.name}</span>
          </div>
          {hasProfile && (
            <Button variant="ghost" onClick={() => navigate("/today")}>
              {t.nav.today} <ArrowRight />
            </Button>
          )}
        </header>

        <section className="grid items-center gap-10 md:grid-cols-[1.1fr_1fr]">
          <div className="animate-fade-up space-y-6">
            <p className="inline-flex rounded-full bg-accent/15 px-3 py-1 text-xs font-bold uppercase tracking-wide text-accent-foreground dark:text-accent">
              {t.app.tagline}
            </p>
            <h1 className="text-balance text-3xl font-bold leading-[1.15] md:text-5xl">{t.landing.title}</h1>
            <p className="text-lg text-muted-foreground">{t.landing.lead}</p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button size="lg" onClick={() => navigate(hasProfile ? "/recommendations" : "/onboarding")}>
                {t.landing.start} <ArrowRight />
              </Button>
              <Button size="lg" variant="outline" onClick={tryDemo} disabled={demo.isPending}>
                {demo.isPending && <Loader2 className="animate-spin" />}
                {t.landing.demo}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">{t.landing.noLogin}</p>
          </div>

          <div className="relative" aria-label={t.landing.previewTitle}>
            <div className="absolute -inset-4 -z-10 rounded-[2rem] bg-gradient-to-br from-primary/15 via-accent/10 to-transparent blur-2xl" />
            <p className="mb-3 text-xs font-bold uppercase tracking-wide text-muted-foreground">{t.landing.previewTitle}</p>
            <div className="space-y-3">
              {t.landing.previewCards.map((c, i) => (
                <Card key={c.name} className="animate-fade-up p-4" style={{ animationDelay: `${120 + i * 90}ms` }}>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="truncate font-semibold">{c.name}</span>
                    <TierBadge tier={c.tier as Tier} />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {c.reasons.map((r, j) => (
                      <ReasonChip key={r} reason={{ kind: j === 1 && c.tier === "dream" ? "risk" : "plus", text: r }} />
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-xl font-bold">{t.landing.howTitle}</h2>
          <div className="grid gap-3 md:grid-cols-3">
            {t.landing.how.map((h, i) => (
              <Card key={h.title} className="p-5">
                <span className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-display text-sm font-bold text-primary">
                  {i + 1}
                </span>
                <p className="font-semibold">{h.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{h.text}</p>
              </Card>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
