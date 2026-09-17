import type { Profile } from "@/api/types";
import { gpa5to4 } from "./format";
export type Scale = "5" | "4" | "100" | "ib8";
export type Academic = { scale: Scale; value: number };
export const scales: Record<
  Scale,
  { label: string; max: number; step: number }
> = {
  "5": { label: "Из 5", max: 5, step: 0.1 },
  "4": { label: "GPA / 4", max: 4, step: 0.1 },
  "100": { label: "Из 100", max: 100, step: 1 },
  ib8: { label: "IB MYP / 8", max: 8, step: 0.1 },
};
export function academicOf(profile: Profile): Academic | null {
  return (
    profile.academic_record ??
    (profile.gpa5 != null ? { scale: "5", value: profile.gpa5 } : null)
  );
}
export function academicGpa4(profile: Profile): number | null {
  const a = academicOf(profile);
  if (!a) return null;
  if (a.scale === "4") return a.value;
  return a.scale === "5" && a.value >= 2 ? gpa5to4(a.value) : null;
}
export function academicLabel(profile: Profile): string {
  const a = academicOf(profile);
  return a
    ? `${a.value} / ${scales[a.scale].max}${a.scale === "ib8" ? " · критерий IB MYP" : ""}`
    : "Пока не указан";
}
