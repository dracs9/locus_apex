import type { Profile, ProfileIn } from "@/api/types";

/** Saved profile -> PUT /me/profile body. Achievements are managed separately, so none are sent. */
export function profileToIn(profile: Profile, patch: Partial<ProfileIn> = {}): ProfileIn {
  return {
    grade: profile.grade,
    gpa5: profile.gpa5 ?? null,
    academic_record: profile.academic_record ?? null,
    holland: profile.holland ?? null,
    majors: profile.majors,
    countries: profile.countries,
    budget_per_year_usd: profile.budget_per_year_usd,
    needs_aid: profile.needs_aid,
    intake_year: profile.intake_year,
    priorities: profile.priorities,
    initial_achievements: [],
    ...patch,
  };
}
