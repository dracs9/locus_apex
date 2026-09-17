import { ArrowRight, ChevronDown, Flag, ListChecks, Pencil, Settings, ShieldAlert, Sparkles, Target } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useMajors, usePassportText, useProfile } from "@/api/hooks";
import type { PassportItem } from "@/api/types";
import { GeneratedMark } from "@/components/ds/badges";
import { Card, PageHeader } from "@/components/ds/Card";
import { ErrorState } from "@/components/ds/states";
import { useProfileEditor } from "@/components/profile/ProfileEditorSheet";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { profileFieldAnswer } from "@/lib/profileFields";
import { cn } from "@/lib/utils";

function Item({ item, answer, tone }: { item: PassportItem; answer: { label: string; value: string }; tone: "plus" | "risk" | "blocker" | "neutral" }) {
  const [open, setOpen] = useState(false);
  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={cn(
          "flex w-full items-start gap-2 rounded-md px-3 py-2.5 text-left text-sm font-medium transition-colors",
          tone === "plus" && "bg-plus-soft/60 hover:bg-plus-soft",
          tone === "risk" && "bg-risk-soft/60 hover:bg-risk-soft",
          tone === "blocker" && "bg-blocker-soft/60 hover:bg-blocker-soft",
          tone === "neutral" && "bg-muted/60 hover:bg-muted",
        )}
      >
        <span className="flex-1">{item.text}</span>
        <ChevronDown className={cn("mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <p className="px-3 pt-1.5 text-xs text-muted-foreground">
          {t.passport.sourceAnswer} <span className="font-semibold text-foreground">{answer.label}</span> — {answer.value}
        </p>
      )}
    </li>
  );
}

function Block({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <Card className="p-4">
      <h2 className="mb-3 flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-wide text-muted-foreground">
        {icon}
        {title}
      </h2>
      <ul className="space-y-2">{children}</ul>
    </Card>
  );
}

export function Passport() {
  const navigate = useNavigate();
  const profile = useProfile();
  const passport = usePassportText(!!profile.data);
  const majors = useMajors();
  const openEditor = useProfileEditor((s) => s.setOpen);
  const majorNames = new Map((majors.data ?? []).map((m) => [m.id, m.name_ru]));

  if (!profile.data) return null;
  const answer = (field: string) => profileFieldAnswer(profile.data, field, majorNames);

  return (
    <div className="space-y-5">
      <PageHeader
        title={t.passport.title}
        subtitle={passport.data && <GeneratedMark generated={passport.data.generated} />}
        actions={
          <Button variant="outline" size="sm" onClick={() => openEditor(true)}>
            <Pencil /> {t.passport.editProfile}
          </Button>
        }
      />

      {passport.isPending && (
        <div className="grid gap-3 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-36" />
          ))}
        </div>
      )}
      {passport.isError && !passport.data && <ErrorState onRetry={() => passport.refetch()} />}

      {passport.data && (
        <>
          <Card className="relative overflow-hidden border-primary/30 bg-gradient-to-br from-primary/10 to-transparent p-5">
            <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-primary">
              <Flag className="h-4 w-4" /> {t.passport.goal}
            </p>
            <p className="font-display text-lg font-bold leading-snug md:text-xl">{passport.data.goal.text}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              {t.passport.sourceAnswer} {answer(passport.data.goal.profile_field).value}
            </p>
          </Card>

          <div className="grid gap-3 md:grid-cols-2">
            <Block icon={<Sparkles className="h-4 w-4 text-plus" />} title={t.passport.strengths}>
              {passport.data.strengths.map((s) => (
                <Item key={s.text} item={s} answer={answer(s.profile_field)} tone="plus" />
              ))}
            </Block>
            <Block icon={<Target className="h-4 w-4 text-muted-foreground" />} title={t.passport.constraints}>
              {passport.data.constraints.map((s) => (
                <Item key={s.text} item={s} answer={answer(s.profile_field)} tone="neutral" />
              ))}
            </Block>
          </div>

          <Block icon={<ShieldAlert className="h-4 w-4 text-risk" />} title={t.passport.risk}>
            <Item item={passport.data.risk} answer={answer(passport.data.risk.profile_field)} tone="risk" />
          </Block>
        </>
      )}

      <Button size="lg" className="w-full md:w-auto" onClick={() => navigate("/recommendations")}>
        {t.passport.showOptions} <ArrowRight />
      </Button>

      <div className="grid grid-cols-2 gap-2 md:hidden">
        <Button variant="outline" asChild>
          <Link to="/history">
            <ListChecks /> {t.nav.achievements}
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/settings">
            <Settings /> {t.nav.settings}
          </Link>
        </Button>
      </div>

    </div>
  );
}
