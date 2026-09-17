import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { create } from "zustand";

import { useMajors, useProfile, useSaveProfile, useUniversities } from "@/api/hooks";
import type { Profile } from "@/api/types";
import { Pill } from "@/components/ds/badges";
import { Button } from "@/components/ui/button";
import { Input, Label, Switch } from "@/components/ui/misc";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { Slider } from "@/components/ui/slider";
import { t } from "@/i18n/ru";
import { countryName, gpa5to4, money } from "@/lib/format";
import { useNetwork } from "@/store/ui";

export const useProfileEditor = create<{ open: boolean; setOpen: (open: boolean) => void }>((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}));

const schema = z.object({
  grade: z.union([z.literal(10), z.literal(11), z.literal(12)]),
  gpa5: z.number().min(2).max(5),
  majors: z.array(z.string()).min(1, "Выберите хотя бы одно направление").max(3),
  countries: z.array(z.string()).min(1, "Выберите хотя бы одну страну"),
  budget_per_year_usd: z.number().int().min(0).max(500000),
  needs_aid: z.boolean(),
  intake_year: z.number().int().min(2025).max(2035),
});
type FormValues = z.infer<typeof schema>;

function EditorForm({ profile, onDone }: { profile: Profile; onDone: () => void }) {
  const majors = useMajors();
  const universities = useUniversities();
  const save = useSaveProfile();
  const offline = useNetwork((s) => s.offline);
  const countries = [...new Set((universities.data ?? []).map((u) => u.country))];

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      grade: profile.grade,
      gpa5: profile.gpa5,
      majors: profile.majors,
      countries: profile.countries,
      budget_per_year_usd: profile.budget_per_year_usd,
      needs_aid: profile.needs_aid,
      intake_year: profile.intake_year,
    },
  });
  const errors = form.formState.errors;

  const submit = form.handleSubmit(async (v) => {
    await save.mutateAsync({ ...v, priorities: profile.priorities, initial_achievements: [] });
    onDone();
  });

  const toggle = (list: string[], id: string, max: number) =>
    list.includes(id) ? list.filter((x) => x !== id) : list.length < max ? [...list, id] : list;

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <Controller
        control={form.control}
        name="budget_per_year_usd"
        render={({ field }) => (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="pe-budget">{t.profileEditor.budget}</Label>
              <span className="font-display font-bold">{money(field.value)}</span>
            </div>
            <Slider aria-label={t.profileEditor.budget} min={0} max={100000} step={1000} value={[Math.min(field.value, 100000)]} onValueChange={([v]) => field.onChange(v)} />
            <Input id="pe-budget" inputMode="numeric" value={field.value} onChange={(e) => field.onChange(Number(e.target.value.replace(/\D/g, "")) || 0)} />
          </div>
        )}
      />

      <Controller
        control={form.control}
        name="needs_aid"
        render={({ field }) => (
          <div className="flex items-center justify-between gap-3 rounded-md border p-3">
            <Label htmlFor="pe-aid">{t.profileEditor.needsAid}</Label>
            <Switch id="pe-aid" checked={field.value} onCheckedChange={field.onChange} />
          </div>
        )}
      />

      <Controller
        control={form.control}
        name="majors"
        render={({ field }) => (
          <div className="space-y-2">
            <Label>{t.profileEditor.majors}</Label>
            <div className="flex flex-wrap gap-2">
              {(majors.data ?? []).map((m) => (
                <Pill key={m.id} active={field.value.includes(m.id)} onClick={() => field.onChange(toggle(field.value, m.id, 3))} className="min-h-9 px-3 py-1.5 text-xs">
                  {m.name_ru}
                </Pill>
              ))}
            </div>
            {errors.majors && <p className="text-xs text-blocker">{errors.majors.message}</p>}
          </div>
        )}
      />

      <Controller
        control={form.control}
        name="countries"
        render={({ field }) => (
          <div className="space-y-2">
            <Label>{t.profileEditor.countries}</Label>
            <div className="flex flex-wrap gap-2">
              {countries.map((c) => (
                <Pill key={c} active={field.value.includes(c)} onClick={() => field.onChange(toggle(field.value, c, 10))} className="min-h-9 px-3 py-1.5 text-xs">
                  {countryName(c)}
                </Pill>
              ))}
            </div>
            {errors.countries && <p className="text-xs text-blocker">{errors.countries.message}</p>}
          </div>
        )}
      />

      <Controller
        control={form.control}
        name="gpa5"
        render={({ field }) => (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <Label>{t.profileEditor.gpa}</Label>
              <span className="text-sm font-bold">
                {field.value.toFixed(1)} <span className="font-normal text-muted-foreground">≈ {gpa5to4(field.value).toFixed(1)} GPA</span>
              </span>
            </div>
            <Slider aria-label={t.profileEditor.gpa} min={2} max={5} step={0.1} value={[field.value]} onValueChange={([v]) => field.onChange(Math.round(v * 10) / 10)} />
            <p className="text-xs text-muted-foreground">{t.common.approxGpa}</p>
          </div>
        )}
      />

      <div className="grid grid-cols-2 gap-3">
        <Controller
          control={form.control}
          name="grade"
          render={({ field }) => (
            <div className="space-y-2">
              <Label>{t.profileEditor.grade}</Label>
              <div className="flex gap-1.5">
                {([10, 11, 12] as const).map((g) => (
                  <Pill key={g} active={field.value === g} onClick={() => field.onChange(g)} className="min-h-9 flex-1 justify-center px-2 py-1.5">
                    {g}
                  </Pill>
                ))}
              </div>
            </div>
          )}
        />
        <div className="space-y-2">
          <Label htmlFor="pe-intake">{t.profileEditor.intakeYear}</Label>
          <Input id="pe-intake" type="number" inputMode="numeric" {...form.register("intake_year", { valueAsNumber: true })} />
        </div>
      </div>

      <Button type="submit" size="lg" className="w-full" disabled={save.isPending || offline}>
        {save.isPending && <Loader2 className="animate-spin" />}
        {offline ? t.common.offlineEditsDisabled : save.isPending ? t.profileEditor.saving : t.common.save}
      </Button>
    </form>
  );
}

export function ProfileEditorSheet() {
  const { open, setOpen } = useProfileEditor();
  const profile = useProfile();
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent>
        <SheetTitle>{t.profileEditor.title}</SheetTitle>
        <SheetDescription className="sr-only">{t.profileEditor.title}</SheetDescription>
        {profile.data && open && <EditorForm profile={profile.data} onDone={() => setOpen(false)} />}
      </SheetContent>
    </Sheet>
  );
}
