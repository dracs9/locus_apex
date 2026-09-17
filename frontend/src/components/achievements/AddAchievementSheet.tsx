import { zodResolver } from "@hookform/resolvers/zod";
import { Award, BookOpenCheck, FolderGit2, Globe2, HandHeart, Languages, Loader2, MoreHorizontal, Trophy } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { create } from "zustand";

import { useAddAchievement, usePatchAchievement } from "@/api/hooks";
import type { Achievement, AchievementType } from "@/api/types";
import { Pill } from "@/components/ds/badges";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/misc";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { t } from "@/i18n/ru";
import { todayIso } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useNetwork } from "@/store/ui";

type Level = NonNullable<Achievement["level"]>;

interface SheetState {
  open: boolean;
  type: AchievementType | null;
  editing: Achievement | null;
  openNew: (type?: AchievementType) => void;
  openEdit: (a: Achievement) => void;
  close: () => void;
}

export const useAchievementSheet = create<SheetState>((set) => ({
  open: false,
  type: null,
  editing: null,
  openNew: (type) => set({ open: true, type: type ?? null, editing: null }),
  openEdit: (a) => set({ open: true, type: a.type, editing: a }),
  close: () => set({ open: false }),
}));

const EXAMS: Record<string, { min: number; max: number; step: number }> = {
  SAT: { min: 400, max: 1600, step: 10 },
  IELTS: { min: 0, max: 9, step: 0.5 },
  TOEFL: { min: 0, max: 120, step: 1 },
};

const PRESETS: { type: AchievementType; icon: typeof Award }[] = [
  { type: "SAT", icon: BookOpenCheck },
  { type: "IELTS", icon: Languages },
  { type: "TOEFL", icon: Globe2 },
  { type: "OLYMPIAD", icon: Trophy },
  { type: "PROJECT", icon: FolderGit2 },
  { type: "COMPETITION", icon: Award },
  { type: "VOLUNTEER", icon: HandHeart },
  { type: "OTHER", icon: MoreHorizontal },
];

const LEVELS: Level[] = ["school", "city", "national", "international"];

function schemaFor(type: AchievementType) {
  const exam = EXAMS[type];
  return z
    .object({
      score: z.string(),
      title: z.string().max(120),
      level: z.enum(["school", "city", "national", "international"]).nullable(),
      date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Укажите дату"),
      status: z.enum(["done", "planned"]),
    })
    .superRefine((v, ctx) => {
      if (exam && v.status === "done") {
        const n = Number(v.score.replace(",", "."));
        if (!v.score || Number.isNaN(n) || n < exam.min || n > exam.max)
          ctx.addIssue({ code: "custom", path: ["score"], message: `Балл от ${exam.min} до ${exam.max}` });
      }
      if (!exam && !v.title.trim()) ctx.addIssue({ code: "custom", path: ["title"], message: "Назовите достижение" });
    });
}

type FormValues = z.infer<ReturnType<typeof schemaFor>>;

function AchievementForm({ type, editing, onDone }: { type: AchievementType; editing: Achievement | null; onDone: () => void }) {
  const add = useAddAchievement();
  const patch = usePatchAchievement();
  const offline = useNetwork((s) => s.offline);
  const exam = EXAMS[type];
  const form = useForm<FormValues>({
    resolver: zodResolver(schemaFor(type)),
    defaultValues: {
      score: editing?.score != null ? String(editing.score) : "",
      title: editing?.title ?? "",
      level: editing?.level ?? (exam ? null : "school"),
      date: editing?.date ?? todayIso(),
      status: editing?.status ?? "done",
    },
  });
  const status = form.watch("status");
  const pending = add.isPending || patch.isPending;

  const submit = form.handleSubmit(async (v) => {
    const body = {
      type,
      score: exam && v.score ? Number(v.score.replace(",", ".")) : null,
      title: v.title.trim() || null,
      level: exam ? null : v.level,
      date: v.date,
      status: v.status,
    };
    if (editing) await patch.mutateAsync({ id: editing.id, body });
    else await add.mutateAsync(body);
    onDone();
  });

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <div className="grid grid-cols-2 gap-2">
        {(["done", "planned"] as const).map((s) => (
          <Pill key={s} active={status === s} onClick={() => form.setValue("status", s)} className="justify-center">
            {s === "done" ? t.achievements.done : t.achievements.planned}
          </Pill>
        ))}
      </div>
      {status === "planned" && <p className="text-xs text-muted-foreground">{t.achievements.plannedNote}</p>}

      {exam ? (
        <div className="space-y-1.5">
          <Label htmlFor="ach-score">{t.achievements.score}</Label>
          <Input
            id="ach-score"
            inputMode="decimal"
            autoFocus={!editing}
            placeholder={`${exam.min}–${exam.max}`}
            {...form.register("score")}
          />
          {form.formState.errors.score && <p className="text-xs text-blocker">{form.formState.errors.score.message}</p>}
        </div>
      ) : (
        <>
          <div className="space-y-1.5">
            <Label htmlFor="ach-title">{t.achievements.titleField}</Label>
            <Input id="ach-title" autoFocus={!editing} placeholder="Например: призёр областной олимпиады по физике" {...form.register("title")} />
            {form.formState.errors.title && <p className="text-xs text-blocker">{form.formState.errors.title.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>{t.achievements.level}</Label>
            <Controller
              control={form.control}
              name="level"
              render={({ field }) => (
                <div className="flex flex-wrap gap-2">
                  {LEVELS.map((l) => (
                    <Pill key={l} active={field.value === l} onClick={() => field.onChange(l)} className="min-h-9 px-3 py-1.5 text-xs">
                      {t.achievements.levels[l]}
                    </Pill>
                  ))}
                </div>
              )}
            />
          </div>
        </>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="ach-date">{t.achievements.date}</Label>
        <Input id="ach-date" type="date" {...form.register("date")} />
        {form.formState.errors.date && <p className="text-xs text-blocker">{form.formState.errors.date.message}</p>}
      </div>

      <Button type="submit" size="lg" className="w-full" disabled={pending || offline}>
        {pending && <Loader2 className="animate-spin" />}
        {offline ? t.common.offlineEditsDisabled : t.common.save}
      </Button>
    </form>
  );
}

export function AddAchievementSheet() {
  const { open, type, editing, close, openNew } = useAchievementSheet();

  return (
    <Sheet open={open} onOpenChange={(o) => !o && close()}>
      <SheetContent>
        <SheetTitle>
          {editing ? t.achievements.edit : type ? `${t.achievements.add}: ${t.achievements.types[type]}` : t.achievements.add}
        </SheetTitle>
        <SheetDescription className="sr-only">{t.achievements.add}</SheetDescription>
        {!type ? (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {PRESETS.map(({ type: p, icon: Icon }) => (
              <button
                key={p}
                type="button"
                onClick={() => openNew(p)}
                className={cn("flex flex-col items-center gap-2 rounded-lg border bg-card p-4 text-sm font-semibold transition-colors hover:border-primary hover:bg-muted")}
              >
                <Icon className="h-6 w-6 text-primary" />
                {t.achievements.types[p]}
              </button>
            ))}
          </div>
        ) : (
          <AchievementForm key={`${type}-${editing?.id ?? "new"}`} type={type} editing={editing} onDone={close} />
        )}
      </SheetContent>
    </Sheet>
  );
}
