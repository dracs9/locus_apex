import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Trash2 } from "lucide-react";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { create } from "zustand";

import { useAddStep, useDeleteStep, usePatchStep } from "@/api/hooks";
import type { RoadmapStep, StepKind } from "@/api/types";
import { Pill } from "@/components/ds/badges";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/misc";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { t } from "@/i18n/ru";
import { toIsoDate } from "@/lib/format";
import { useNetwork } from "@/store/ui";

export const STEP_KINDS: StepKind[] = ["activity", "exam", "document", "academic", "application"];

interface StepSheetState {
  open: boolean;
  editing: RoadmapStep | null;
  openNew: () => void;
  openEdit: (step: RoadmapStep) => void;
  close: () => void;
}

export const useStepSheet = create<StepSheetState>((set) => ({
  open: false,
  editing: null,
  openNew: () => set({ open: true, editing: null }),
  openEdit: (step) => set({ open: true, editing: step }),
  close: () => set({ open: false }),
}));

const schema = z.object({
  title: z.string().trim().min(1, t.roadmap.sheet.titleRequired).max(200),
  kind: z.enum(["activity", "exam", "document", "academic", "application"]),
  due_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, t.roadmap.sheet.dateRequired),
  note: z.string().max(1000),
});
type FormValues = z.infer<typeof schema>;

function defaults(step: RoadmapStep | null): FormValues {
  if (step) return { title: step.title, kind: step.kind, due_date: step.due_date, note: step.note ?? "" };
  const inAMonth = new Date();
  inAMonth.setDate(inAMonth.getDate() + 30);
  return { title: "", kind: "activity", due_date: toIsoDate(inAMonth), note: "" };
}

function StepForm({ editing, onDone }: { editing: RoadmapStep | null; onDone: () => void }) {
  const add = useAddStep();
  const patch = usePatchStep();
  const remove = useDeleteStep();
  const offline = useNetwork((s) => s.offline);
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: defaults(editing) });
  const busy = add.isPending || patch.isPending || remove.isPending;

  useEffect(() => form.reset(defaults(editing)), [editing, form]);

  const submit = form.handleSubmit(async (v) => {
    const body = { title: v.title.trim(), kind: v.kind, due_date: v.due_date, note: v.note.trim() || null };
    try {
      if (editing) await patch.mutateAsync({ id: editing.id, ...body });
      else await add.mutateAsync(body);
      onDone();
    } catch {
      /* the mutation shows the error; the form keeps the input */
    }
  });

  const errors = form.formState.errors;
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <div className="space-y-1.5">
        <Label htmlFor="step-title">{t.roadmap.sheet.title}</Label>
        <Input id="step-title" autoFocus={!editing} placeholder={t.roadmap.sheet.titlePlaceholder} {...form.register("title")} />
        {errors.title && <p className="text-xs text-blocker">{errors.title.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label>{t.roadmap.sheet.kind}</Label>
        <Controller
          control={form.control}
          name="kind"
          render={({ field }) => (
            <div className="flex flex-wrap gap-2">
              {STEP_KINDS.map((k) => (
                <Pill key={k} active={field.value === k} onClick={() => field.onChange(k)}>
                  {t.roadmap.kinds[k]}
                </Pill>
              ))}
            </div>
          )}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="step-date">{t.roadmap.sheet.date}</Label>
        <Input id="step-date" type="date" {...form.register("due_date")} />
        {errors.due_date && <p className="text-xs text-blocker">{errors.due_date.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="step-note">{t.roadmap.sheet.note}</Label>
        <textarea
          id="step-note"
          rows={3}
          placeholder={t.roadmap.sheet.notePlaceholder}
          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm"
          {...form.register("note")}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2 pt-1">
        {editing && (
          <Button
            type="button"
            variant="ghost"
            className="text-blocker"
            disabled={busy || offline}
            onClick={async () => {
              try {
                await remove.mutateAsync(editing.id);
                onDone();
              } catch {
                /* toast shown by the mutation */
              }
            }}
          >
            <Trash2 /> {t.roadmap.sheet.delete}
          </Button>
        )}
        <div className="flex-1" />
        <Button type="submit" disabled={busy || offline}>
          {busy && <Loader2 className="animate-spin" />}
          {editing ? t.common.save : t.roadmap.sheet.add}
        </Button>
      </div>
    </form>
  );
}

/** Add a custom step to the plan, or edit / delete an existing one. */
export function StepSheet() {
  const { open, editing, close } = useStepSheet();
  return (
    <Sheet open={open} onOpenChange={(o) => !o && close()}>
      <SheetContent>
        <SheetTitle>{editing ? t.roadmap.sheet.editTitle : t.roadmap.sheet.newTitle}</SheetTitle>
        <SheetDescription>{editing ? t.roadmap.sheet.editHint : t.roadmap.sheet.newHint}</SheetDescription>
        {open && <StepForm editing={editing} onDone={close} />}
      </SheetContent>
    </Sheet>
  );
}
