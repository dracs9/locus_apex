import type { Profile } from "@/api/types";

import { academicOf } from "./academic";

const ACTIVITY_TYPES = ["OLYMPIAD", "PROJECT", "VOLUNTEER", "COMPETITION", "OTHER"];

/** How much of the profile is filled in (0..1) and what is still missing. Not an admission chance. */
export function profileCompleteness(profile: Profile, favoritesCount: number): { value: number; missing: string[] } {
  const done = (type: string) => profile.achievements.some((a) => a.type === type && a.status === "done");
  const checks: [boolean, string][] = [
    [academicOf(profile) != null, "Средний балл в школе"],
    [!!profile.holland, "Тест интересов Холланда"],
    [done("SAT"), "Результат SAT"],
    [done("IELTS") || done("TOEFL"), "Результат IELTS или TOEFL"],
    [profile.achievements.some((a) => ACTIVITY_TYPES.includes(a.type) && a.status === "done"), "Хотя бы одна активность в портфолио"],
    [favoritesCount >= 3, "3 сохранённых вуза"],
    [Object.values(profile.priorities).some((v) => v !== 0.5), "Свои приоритеты (цена, престиж, помощь, страна)"],
    [profile.majors.length >= 2 || profile.countries.length >= 2, "Запасное направление или страна"],
  ];
  return {
    value: checks.filter(([ok]) => ok).length / checks.length,
    missing: checks.filter(([ok]) => !ok).map(([, label]) => label),
  };
}
