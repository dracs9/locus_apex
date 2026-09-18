import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Academic, Scale } from "@/lib/academic";
import type { Answers } from "@/lib/interests";

import type { Priorities } from "@/api/types";

export interface OnboardingDraft {
  step: number;
  grade: 9 | 10 | 11 | 12 | null;
  academic: Academic | null;
  scale: Scale;
  hollandAnswers: Answers;
  gpa5: number | null;
  majors: string[];
  countries: string[];
  budget: number | null;
  budgetUnknown: boolean;
  needsAid: boolean | null;
  sat: string;
  ielts: string;
  toefl: string;
  priorities: Priorities;
}

const initial: OnboardingDraft = {
  step: 0,
  grade: null,
  academic: null,
  scale: "5",
  hollandAnswers: {},
  gpa5: null,
  majors: [],
  countries: [],
  budget: null,
  budgetUnknown: false,
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
    {
      name: "onboarding-draft",
      version: 2,
      migrate: (old) => ({
        ...initial,
        ...(old as Partial<OnboardingDraft>),
        step: 0,
      }),
    },
  ),
);
