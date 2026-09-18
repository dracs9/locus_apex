import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMajors, useProfile, useSaveProfile } from "@/api/hooks";
import type { Profile } from "@/api/types";
import { HollandQuiz } from "@/components/interests/HollandQuiz";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ds/Card";
import { complete, suggestedMajors } from "@/lib/interests";
import { useNetwork } from "@/store/ui";

function InterestEditor({ profile }: { profile: Profile }) {
  const [answers, setAnswers] = useState(profile.holland?.answers ?? {});
  const [useSuggestions, setUseSuggestions] = useState(false);
  const majors = useMajors();
  const save = useSaveProfile();
  const navigate = useNavigate();
  const offline = useNetwork((s) => s.offline);
  const suggestions = suggestedMajors(
    answers,
    (majors.data ?? []).map((m) => m.id),
  );
  const submit = async () => {
    if (!complete(answers)) return;
    try {
      await save.mutateAsync({
        ...profile,
        holland: { version: "applyra-riasec-v1", answers },
        majors:
          useSuggestions && suggestions.length ? suggestions : profile.majors,
        initial_achievements: [],
      });
      navigate("/passport");
    } catch {
      /* Mutation reports errors, answers stay in the form. */
    }
  };
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Мои интересы"
        subtitle="Можно изменить ответы: профиль интересов развивается вместе с вами."
      />
      <HollandQuiz answers={answers} onChange={setAnswers} />
      {complete(answers) && suggestions.length > 0 && (
        <label className="flex items-start gap-3 rounded-xl border bg-card p-4 text-sm">
          <input
            className="mt-1 h-5 w-5 accent-primary"
            type="checkbox"
            checked={useSuggestions}
            onChange={(e) => setUseSuggestions(e.target.checked)}
          />
          <span>
            Также обновить направления по тесту:{" "}
            <b>
              {suggestions
                .map((id) => majors.data?.find((m) => m.id === id)?.name_ru)
                .join(", ")}
            </b>
            . Без этой отметки ваши выбранные направления сохранятся.
          </span>
        </label>
      )}
      <div className="sticky bottom-16 flex justify-between gap-3 rounded-xl border bg-card/95 p-4 backdrop-blur md:bottom-4">
        <Button variant="outline" onClick={() => navigate("/passport")}>
          Отмена
        </Button>
        <Button
          onClick={submit}
          disabled={!complete(answers) || save.isPending || offline}
        >
          {save.isPending ? "Обновляем маршрут…" : "Сохранить интересы"}
        </Button>
      </div>
    </div>
  );
}
export function Interests() {
  const profile = useProfile();
  return profile.data ? <InterestEditor profile={profile.data} /> : null;
}
