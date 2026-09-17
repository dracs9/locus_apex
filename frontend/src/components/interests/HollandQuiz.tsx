import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/misc";
import {
  complete,
  holland,
  interestScores,
  hollandCode,
  type Answers,
} from "@/lib/interests";
const choices = [
  "Совсем не интересно",
  "Скорее не интересно",
  "Нейтрально",
  "Скорее интересно",
  "Очень интересно",
];

export function HollandQuiz({
  answers,
  onChange,
}: {
  answers: Answers;
  onChange: (answers: Answers) => void;
}) {
  const [page, setPage] = useState(0);
  const questions = holland.questions.slice(page * 6, page * 6 + 6);
  const answered = holland.questions.filter(
    (q) => answers[q.id] != null,
  ).length;
  return (
    <div className="space-y-5">
      <p className="text-sm leading-relaxed text-muted-foreground">
        Оценивайте интерес, а не свои навыки, престиж профессии или ожидаемую
        зарплату. Здесь нет правильных ответов.
      </p>
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-semibold">
          <span>Ответов: {answered} / 30</span>
          <span>Блок {page + 1} / 5</span>
        </div>
        <Progress value={answered / 30} />
      </div>
      {questions.map((q, i) => (
        <fieldset key={q.id} className="rounded-xl border bg-card p-4 md:p-5">
          <legend className="sr-only">{q.text}</legend>
          <p className="mb-4 text-sm font-semibold leading-relaxed">
            <span className="mr-2 text-primary">
              {String(page * 6 + i + 1).padStart(2, "0")}.
            </span>
            {q.text}
          </p>
          <div className="grid grid-cols-5 gap-2">
            {choices.map((label, v) => (
              <label
                key={v}
                className={`flex min-h-12 cursor-pointer flex-col items-center justify-center rounded-lg border p-2 text-center transition-colors ${answers[q.id] === v ? "border-primary bg-primary/10 text-primary" : "hover:bg-muted"}`}
              >
                <input
                  className="sr-only peer"
                  type="radio"
                  name={q.id}
                  value={v}
                  checked={answers[q.id] === v}
                  onChange={() => onChange({ ...answers, [q.id]: v })}
                  aria-label={label}
                />
                <span className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold peer-focus-visible:ring-2 peer-focus-visible:ring-primary">
                  {v + 1}
                </span>
                <span className="mt-1 hidden text-[11px] leading-tight md:block">
                  {label}
                </span>
              </label>
            ))}
          </div>
          <div className="mt-2 flex justify-between gap-4 text-[11px] text-muted-foreground md:hidden">
            <span>1 — не интересно</span>
            <span>5 — очень интересно</span>
          </div>
        </fieldset>
      ))}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
        >
          Предыдущий блок
        </Button>
        <Button
          disabled={page === 4 || questions.some((q) => answers[q.id] == null)}
          onClick={() => {
            setPage((p) => p + 1);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        >
          Следующий блок
        </Button>
      </div>
      {complete(answers) && <HollandResult answers={answers} />}
    </div>
  );
}

export function HollandResult({ answers }: { answers: Answers }) {
  const code = hollandCode(answers);
  const scores = interestScores(answers).sort((a, b) => b.score - a.score);
  const tied =
    scores[0].score === scores[1].score || scores[2].score === scores[3].score;
  return (
    <section className="rounded-xl border border-primary/20 bg-primary/5 p-5 space-y-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-primary">
          Твой профиль интересов
        </p>
        <h2 className="mt-2 text-2xl font-bold">
          {code ? `Код Холланда: ${code}` : "Интересы пока не разделились"}
        </h2>
      </div>
      <div className="space-y-3">
        {scores.map((s) => (
          <div key={s.code}>
            <div className="mb-1 flex justify-between text-sm">
              <span>
                <b className="text-primary">{s.code}</b> · {s.label}
              </span>
              <span>{s.score} / 20</span>
            </div>
            <Progress value={s.score / 20} />
          </div>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">
        {!code
          ? "Одинаковые баллы не выделяют одно направление. Попробуйте разные проекты и вернитесь к вопросам позже."
          : tied
            ? "Есть равные баллы: порядок букв условный. Изучите все направления с близкими результатами."
            : "Начните с ведущих направлений и проверьте интерес небольшим проектом. Результат можно пересмотреть."}
      </p>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Авторский опросник applyra по модели RIASEC, 30 вопросов. Не официальный
        тест Truity и не профессиональная диагностика. Баллы отражают ответы, а
        не способности или вероятность поступления.{" "}
        <a
          className="underline"
          href="https://www.truity.com/test/holland-code-career-test"
          target="_blank"
          rel="noreferrer"
        >
          Тест Truity ↗
        </a>
      </p>
    </section>
  );
}
