import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Priorities } from "@/api/types";

export interface OnboardingDraft {
  step: number;
  grade: 10 | 11 | 12 | null;
  gpa5: number | null;
  majors: string[];
  countries: string[];
  budget: number | null;
  needsAid: boolean | null;
  sat: string;
  ielts: string;
  toefl: string;
  priorities: Priorities;
}

const initial: OnboardingDraft = {
  step: 0,
  grade: null,
  gpa5: null,
  majors: [],
  countries: [],
  budget: null,
  needsAid: null,
  sat: "",
  ielts: "",
  toefl: "",
  priorities: { cost: 0.5, prestige: 0.5, location: 0.5, aid: 0.5 },
};

interface OnboardingState extends OnboardingDraft {
  patch: (p: Partial<OnboardingDraft>) => void;
  reset: () => void;
}

/** Draft is kept (and persisted) until the profile is submitted. */
export const useOnboarding = create<OnboardingState>()(
  persist(
    (set) => ({
      ...initial,
      patch: (p) => set(p),
      reset: () => set(initial),
    }),
    { name: "onboarding-draft" },
  ),
);
