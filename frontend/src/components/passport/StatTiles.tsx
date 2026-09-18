import { Bookmark, Check, User } from "lucide-react";
import type { ReactNode } from "react";

import type { Profile } from "@/api/types";
import { Card } from "@/components/ds/Card";
import { t } from "@/i18n/ru";
import { academicOf, scales } from "@/lib/academic";

function Tile({ label, icon, value, of, note }: { label: string; icon: ReactNode; value: ReactNode; of?: string; note: string }) {
  return (
    <Card className="rounded-2xl p-5">
      <div className="flex items-start justify-between gap-2 text-sm text-muted-foreground">
        <span>{label}</span>
        <span className="text-foreground/70">{icon}</span>
      </div>
      <p className="mt-4 font-display text-3xl font-bold leading-none">
        {value}
        {of && <span className="ml-1 text-sm font-medium text-muted-foreground">{of}</span>}
      </p>
      <p className="mt-3 text-sm text-muted-foreground">{note}</p>
    </Card>
  );
}

export function StatTiles({ profile, saved, done, total }: { profile: Profile; saved: number; done: number; total: number }) {
  const academic = academicOf(profile);
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Tile
        label={t.passport.gpa}
        icon={<User className="h-5 w-5" />}
        value={academic ? academic.value : "—"}
        of={`/ ${scales[academic?.scale ?? "5"].max}`}
        note={t.passport.gpaNote}
      />
      <Tile label={t.passport.saved} icon={<Bookmark className="h-5 w-5" />} value={String(saved).padStart(2, "0")} note={t.passport.savedNote} />
      <Tile label={t.passport.steps} icon={<Check className="h-5 w-5" />} value={done} of={`/ ${total}`} note={t.passport.stepsNote} />
    </div>
  );
}
