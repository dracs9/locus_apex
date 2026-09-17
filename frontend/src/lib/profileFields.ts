import { academicLabel } from "./academic";
import { hollandCode } from "./interests";
import type { Profile } from "@/api/types";
import { t } from "@/i18n/ru";

import { countryName, money } from "./format";

function best(profile: Profile, type: string): number | null {
  const scores = profile.achievements.filter((a) => a.type === type && a.status === "done" && a.score != null).map((a) => a.score as number);
  return scores.length ? Math.max(...scores) : null;
}

/** Human answer behind a `profile_field` used in reasons and the passport ("where does this come from"). */
export function profileFieldAnswer(profile: Profile, field: string, majorNames: Map<string, string>): { label: string; value: string } {
  switch (field) {
    case "gpa5":
      return { label: "Средний балл", value: academicLabel(profile) };
    case "holland":
      return { label: "Интересы RIASEC", value: profile.holland ? hollandCode(profile.holland.answers) ?? "Равные интересы" : "Тест ещё не пройден" };
    case "majors":
      return { label: "Направления", value: profile.majors.map((m) => majorNames.get(m) ?? m).join(", ") };
    case "countries":
      return { label: "Страны", value: profile.countries.map(countryName).join(", ") };
    case "budget_per_year_usd":
      return { label: "Бюджет", value: `${money(profile.budget_per_year_usd)} в год` };
    case "needs_aid":
      return { label: "Финпомощь", value: profile.needs_aid ? "нужна" : "не нужна" };
    case "grade":
      return { label: "Класс", value: `${profile.grade}` };
    case "intake_year":
      return { label: "Год поступления", value: `${profile.intake_year}` };
    case "achievement:SAT": {
      const s = best(profile, "SAT");
      return { label: "SAT", value: s == null ? "ещё не сдан" : `${s}` };
    }
    case "achievement:IELTS": {
      const i = best(profile, "IELTS");
      const toefl = best(profile, "TOEFL");
      const parts = [i != null ? `IELTS ${i}` : null, toefl != null ? `TOEFL ${toefl}` : null].filter(Boolean);
      return { label: "Английский", value: parts.length ? parts.join(", ") : "сертификата нет" };
    }
    case "achievements": {
      const list = profile.achievements.filter((a) => a.status === "done" && !["SAT", "IELTS", "TOEFL"].includes(a.type));
      return { label: "Достижения", value: list.length ? list.map((a) => a.title ?? t.achievements.types[a.type]).join("; ") : "пока нет" };
    }
    default:
      if (field.startsWith("priorities.")) {
        const key = field.split(".")[1] as keyof Profile["priorities"];
        return { label: `Приоритет «${t.priorities[key]}»`, value: `${Math.round(profile.priorities[key] * 10)}/10` };
      }
      return { label: field, value: "" };
  }
}
