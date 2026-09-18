import { ArrowRight, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { t } from "@/i18n/ru";

export function AdviceCard({ text, generated }: { text: string; generated: boolean }) {
  return (
    <section className="rounded-2xl bg-hero-dark p-6 text-hero-dark-foreground shadow-lg">
      <h2 className="flex items-center gap-3 text-lg font-bold">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
          <Sparkles className="h-5 w-5" />
        </span>
        {t.passport.adviceTitle}
      </h2>
      <p className="mt-4 leading-relaxed text-hero-dark-foreground/85">{text}</p>
      <Link
        to="/roadmap"
        className="mt-6 flex h-12 items-center justify-center gap-2 rounded-xl bg-white font-bold text-hero-dark transition-opacity hover:opacity-90"
      >
        {t.passport.openPlan} <ArrowRight className="h-4 w-4" />
      </Link>
      <p className="mt-4 text-sm text-hero-dark-foreground/60">{generated ? t.common.aiText : t.common.templateText}</p>
    </section>
  );
}
