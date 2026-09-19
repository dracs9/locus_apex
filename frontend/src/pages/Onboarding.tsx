import { ArrowLeft, ArrowRight, Loader2, Users } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";

import {
  useMajors,
  useProfile,
  useSaveProfile,
  useUniversities,
} from "@/api/hooks";
import type { AchievementIn, ProfileIn } from "@/api/types";
import { Pill } from "@/components/ds/badges";
import { NetworkBanners, ErrorState } from "@/components/ds/states";
import { Button } from "@/components/ui/button";
import { Input, Label, Progress, Skeleton } from "@/components/ui/misc";
import { Logo } from "@/components/brand/Logo";
import { AcademicField } from "@/components/profile/AcademicField";
import { HollandQuiz } from "@/components/interests/HollandQuiz";
import { complete, suggestedMajors } from "@/lib/interests";
import { Slider } from "@/components/ui/slider";
import { t } from "@/i18n/ru";
import { catalogCountries, countryName, intakeYearFor, todayIso } from "@/lib/format";
import { useOnboarding } from "@/store/onboarding";
import { useNetwork } from "@/store/ui";

const STEPS = [
  "grade",
  "gpa",
  "interests",
  "majors",
  "countries",
  "budget",
  "exams",
  "priorities",
] as const;
const PRIORITY_KEYS = ["cost", "prestige", "aid", "location"] as const;

const examSchema = z.object({
  sat: z.union([z.literal(""), z.coerce.number().int().min(400).max(1600)]),
  ielts: z.union([z.literal(""), z.coerce.number().min(0).max(9)]),
  toefl: z.union([z.literal(""), z.coerce.number().int().min(0).max(120)]),
});

function Question({
  title,
  hint,
  children,
}: {
  title: string;
  hint: string;
  children: ReactNode;
}) {
  return (
    <div className="animate-fade-up space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold leading-tight md:text-3xl">
          {title}
        </h1>
        <p className="text-muted-foreground">{hint}</p>
      </div>
      {children}
    </div>
  );
}

export function Onboarding() {
  const navigate = useNavigate();
  const profile = useProfile();
  const draft = useOnboarding();
  const majors = useMajors();
  const universities = useUniversities();
  const save = useSaveProfile({ silent: true });
  const offline = useNetwork((s) => s.offline);

  if (profile.data && !save.isPending && !save.isSuccess)
    return <Navigate to="/passport" replace />;

  const step = STEPS[draft.step];
  const countries = catalogCountries(universities.data ?? []);
  const countByCountry = (c: string) =>
    (universities.data ?? []).filter((u) => u.country === c).length;
  const exams = examSchema.safeParse({
    sat: draft.sat.trim(),
    ielts: draft.ielts.trim().replace(",", "."),
    toefl: draft.toefl.trim(),
  });

  const valid: Record<(typeof STEPS)[number], boolean> = {
    grade: draft.grade !== null,
    gpa: draft.academic !== null,
    interests: complete(draft.hollandAnswers),
    majors: draft.majors.length > 0,
    countries: draft.countries.length > 0,
    budget:
      draft.budget !== null &&
      Number.isSafeInteger(draft.budget) &&
      draft.budget >= 0 &&
      draft.budget <= 500000,
    exams: exams.success,
    priorities: true,
  };

  const next = () => {
    const suggestions =
      step === "interests" && draft.majors.length === 0
        ? suggestedMajors(
            draft.hollandAnswers,
            (majors.data ?? []).map((m) => m.id),
          )
        : draft.majors;
    draft.patch({
      step: Math.min(STEPS.length - 1, draft.step + 1),
      majors: suggestions,
    });
  };
  const back = () =>
    draft.step === 0 ? navigate("/") : draft.patch({ step: draft.step - 1 });

  const dontKnow: Partial<Record<(typeof STEPS)[number], () => void>> = {
    budget: () =>
      draft.patch({ budget: 30000, budgetUnknown: true, step: draft.step + 1 }),
    exams: () =>
      draft.patch({ sat: "", ielts: "", toefl: "", step: draft.step + 1 }),
    priorities: () =>
      draft.patch({
        priorities: { cost: 0.5, prestige: 0.5, location: 0.5, aid: 0.5 },
      }),
  };

  const submit = async () => {
    if (
      !exams.success ||
      draft.grade === null ||
      Object.values(valid).some((v) => !v)
    )
      return;
    const achievements: AchievementIn[] = [];
    const add = (type: AchievementIn["type"], score: number | "") => {
      if (score !== "")
        achievements.push({
          type,
          score,
          date: todayIso(),
          status: "done",
          title: null,
          level: null,
        });
    };
    add("SAT", exams.data.sat);
    add("IELTS", exams.data.ielts);
    add("TOEFL", exams.data.toefl);
    const body: ProfileIn = {
      grade: draft.grade,
      gpa5: null,
      academic_record: draft.academic,
      holland: { version: "applyra-riasec-v1", answers: draft.hollandAnswers },
      majors: draft.majors,
      countries: draft.countries,
      budget_per_year_usd: draft.budget!,
      needs_aid: true,
      intake_year: intakeYearFor(draft.grade),
      priorities: draft.priorities,
      initial_achievements: achievements,
    };
    try {
      await save.mutateAsync(body);
      draft.reset();
      navigate("/passport", { replace: true });
    } catch {
      /* The mutation displays the error; preserve the draft for retry. */
    }
  };

  const toggle = (list: string[], id: string, max: number) =>
    list.includes(id)
      ? list.filter((x) => x !== id)
      : list.length < max
        ? [...list, id]
        : list;

  const catalogError = majors.isError || universities.isError;

  return (
    <div className="flex min-h-dvh flex-col">
      <NetworkBanners />
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-4 pb-8 pt-5">
        <div className="mb-8 flex items-center justify-between">
          <Logo />
          <span className="text-xs font-semibold text-muted-foreground">
            Твой первый шаг
          </span>
        </div>
        <div className="mb-8 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
            <span>{t.onboarding.stepOf(draft.step + 1, STEPS.length)}</span>
            {draft.grade && (
              <span>{t.onboarding.intakeYear(intakeYearFor(draft.grade))}</span>
            )}
          </div>
          <Progress value={(draft.step + 1) / STEPS.length} />
        </div>

        <div className="flex-1">
          {catalogError && (
            <ErrorState
              onRetry={() => {
                void majors.refetch();
                void universities.refetch();
              }}
            />
          )}

          {!catalogError && step === "grade" && (
            <Question
              title={t.onboarding.grade.q}
              hint={t.onboarding.grade.hint}
            >
              <div className="grid grid-cols-4 gap-3">
                {([9, 10, 11, 12] as const).map((g) => (
                  <Pill
                    key={g}
                    active={draft.grade === g}
                    onClick={() => draft.patch({ grade: g, step: 1 })}
                    className="h-16 justify-center text-lg"
                  >
                    {g}
                  </Pill>
                ))}
              </div>
            </Question>
          )}

          {!catalogError && step === "gpa" && (
            <Question title={t.onboarding.gpa.q} hint={t.onboarding.gpa.hint}>
              <AcademicField
                value={draft.academic?.value ?? null}
                scale={draft.scale}
                onChange={(academic) =>
                  draft.patch({ academic, scale: academic.scale })
                }
              />
            </Question>
          )}

          {step === "interests" && (
            <Question
              title="Что тебе интересно делать?"
              hint="Модель Холланда · 30 вопросов · около 5 минут"
            >
              <HollandQuiz
                answers={draft.hollandAnswers}
                onChange={(hollandAnswers) => draft.patch({ hollandAnswers })}
              />
            </Question>
          )}

          {!catalogError && step === "majors" && (
            <Question
              title={t.onboarding.majors.q}
              hint="Первые варианты предложены по RIASEC. Оставьте до трёх направлений или измените выбор; первое — главное."
            >
              {majors.isPending ? (
                <Skeleton className="h-40" />
              ) : (
                <div className="flex flex-wrap gap-2">
                  {(majors.data ?? []).map((m) => {
                    const idx = draft.majors.indexOf(m.id);
                    return (
                      <Pill
                        key={m.id}
                        active={idx >= 0}
                        onClick={() =>
                          draft.patch({ majors: toggle(draft.majors, m.id, 3) })
                        }
                      >
                        {idx >= 0 && (
                          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary-foreground/20 text-[11px]">
                            {idx + 1}
                          </span>
                        )}
                        {m.name_ru}
                      </Pill>
                    );
                  })}
                </div>
              )}
            </Question>
          )}

          {!catalogError && step === "countries" && (
            <Question
              title={t.onboarding.countries.q}
              hint="Выберите страны. США уже есть в каталоге; «скоро» означает, что проверенной подборки по стране ещё нет."
            >
              {universities.isPending ? (
                <Skeleton className="h-32" />
              ) : (
                <div className="flex flex-wrap gap-2">
                  {countries.map((c) => (
                    <Pill
                      key={c}
                      active={draft.countries.includes(c)}
                      onClick={() =>
                        draft.patch({
                          countries: toggle(draft.countries, c, 10),
                        })
                      }
                    >
                      {countryName(c)}
                      <span className="text-xs opacity-70">
                        {countByCountry(c) || "скоро"}
                      </span>
                    </Pill>
                  ))}
                </div>
              )}
            </Question>
          )}

          {!catalogError && step === "budget" && (
            <Question
              title={t.onboarding.budget.q}
              hint={t.onboarding.budget.hint}
            >
              <div className="space-y-4">
                <Label htmlFor="self-budget">Мой вклад за год, USD</Label>
                <Input
                  id="self-budget"
                  inputMode="numeric"
                  placeholder="Например, 5000"
                  value={draft.budget ?? ""}
                  onChange={(e) => {
                    if (/^\d*$/.test(e.target.value))
                      draft.patch({
                        budget:
                          e.target.value === "" ? null : Number(e.target.value),
                        budgetUnknown: false,
                      });
                  }}
                  className="h-16 text-2xl font-bold"
                  aria-describedby="budget-help"
                />
                <p id="budget-help" className="text-sm text-muted-foreground">
                  Обучение и проживание вместе. Укажите 0, если необходимо
                  полное покрытие. Если стоимость выше вашего вклада, проверим
                  варианты финансовой помощи — её получение не гарантировано.
                </p>
                {draft.budgetUnknown && (
                  <p className="text-sm font-semibold text-primary">
                    {t.onboarding.budget.dontKnowNote}
                  </p>
                )}
                <div className="flex gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4">
                  <Users className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                  <div className="space-y-1">
                    <p className="text-sm font-bold">
                      {t.onboarding.budget.parentsTitle}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {t.onboarding.budget.parentsTip}
                    </p>
                  </div>
                </div>
                {draft.budget !== null && !valid.budget && (
                  <p role="alert" className="text-sm text-blocker">
                    Введите целую сумму от 0 до 500 000 USD в год.
                  </p>
                )}
              </div>
            </Question>
          )}

          {!catalogError && step === "exams" && (
            <Question
              title={t.onboarding.exams.q}
              hint={t.onboarding.exams.hint}
            >
              <div className="space-y-4">
                {(
                  [
                    ["sat", t.onboarding.exams.sat, "1350"],
                    ["ielts", t.onboarding.exams.ielts, "6.5"],
                    ["toefl", t.onboarding.exams.toefl, "95"],
                  ] as const
                ).map(([key, label, placeholder]) => (
                  <div key={key} className="space-y-1.5">
                    <Label htmlFor={`exam-${key}`}>{label}</Label>
                    <Input
                      id={`exam-${key}`}
                      inputMode="decimal"
                      placeholder={placeholder}
                      value={draft[key]}
                      onChange={(e) => draft.patch({ [key]: e.target.value })}
                      aria-invalid={
                        !exams.success &&
                        exams.error.issues.some((i) => i.path[0] === key)
                      }
                    />
                    <Slider
                      aria-label={`${label} — ползунок`}
                      min={key === "sat" ? 400 : 0}
                      max={key === "sat" ? 1600 : key === "ielts" ? 9 : 120}
                      step={key === "sat" ? 10 : key === "ielts" ? 0.5 : 1}
                      value={[Number(draft[key]) || (key === "sat" ? 400 : 0)]}
                      onValueChange={([v]) => draft.patch({ [key]: String(v) })}
                    />
                    {!exams.success &&
                      exams.error.issues.some((i) => i.path[0] === key) && (
                        <p className="text-xs text-blocker">
                          Проверьте значение
                        </p>
                      )}
                  </div>
                ))}
              </div>
            </Question>
          )}

          {!catalogError && step === "priorities" && (
            <Question
              title={t.onboarding.priorities.q}
              hint={t.onboarding.priorities.hint}
            >
              <div className="space-y-5">
                {PRIORITY_KEYS.map((k) => (
                  <div key={k} className="space-y-1">
                    <div className="flex justify-between text-sm font-semibold">
                      <span>{t.priorities[k]}</span>
                      <span className="text-muted-foreground">
                        {Math.round(draft.priorities[k] * 10)}/10
                      </span>
                    </div>
                    <Slider
                      aria-label={t.priorities[k]}
                      min={0}
                      max={1}
                      step={0.1}
                      value={[draft.priorities[k]]}
                      onValueChange={([v]) =>
                        draft.patch({
                          priorities: { ...draft.priorities, [k]: v },
                        })
                      }
                    />
                  </div>
                ))}
              </div>
            </Question>
          )}
        </div>

        <div className="sticky bottom-0 mt-8 flex flex-wrap items-center gap-2 bg-background/95 py-3 backdrop-blur">
          <Button variant="ghost" onClick={back} aria-label={t.common.back}>
            <ArrowLeft />{" "}
            <span className="hidden sm:inline">{t.common.back}</span>
          </Button>
          {dontKnow[step] && (
            <Button variant="secondary" onClick={dontKnow[step]}>
              {step === "exams" ? t.onboarding.exams.none : t.common.dontKnow}
            </Button>
          )}
          <div className="flex-1" />
          {draft.step < STEPS.length - 1 ? (
            <Button onClick={next} disabled={!valid[step]}>
              {t.common.next} <ArrowRight />
            </Button>
          ) : (
            <Button
              variant="accent"
              onClick={submit}
              disabled={
                save.isPending ||
                offline ||
                Object.values(valid).some((v) => !v)
              }
            >
              {save.isPending ? <Loader2 className="animate-spin" /> : null}
              {save.isPending ? t.onboarding.building : t.onboarding.finish}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
