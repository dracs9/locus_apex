import { Pill } from "@/components/ds/badges";
import { Slider } from "@/components/ui/slider";
import { scales, type Academic, type Scale } from "@/lib/academic";

export function AcademicField({
  value,
  scale,
  onChange,
}: {
  value: number | null;
  scale: Scale;
  onChange: (a: Academic) => void;
}) {
  const config = scales[scale];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2" aria-label="Шкала оценивания">
        {(Object.keys(scales) as Scale[]).map((s) => (
          <Pill
            key={s}
            active={scale === s}
            onClick={() => onChange({ scale: s, value: 0 })}
          >
            {scales[s].label}
          </Pill>
        ))}
      </div>
      <div className="flex items-baseline gap-2">
        <output className="text-5xl font-extrabold tracking-tight">
          {value ?? "—"}
        </output>
        <span className="text-muted-foreground">/ {config.max}</span>
      </div>
      <Slider
        aria-label="Средний балл"
        min={0}
        max={config.max}
        step={config.step}
        value={[value ?? 0]}
        onValueChange={([v]) =>
          onChange({ scale, value: Math.round(v * 10) / 10 })
        }
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>0</span>
        <span>{config.max}</span>
      </div>
      <p className="rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
        {scale === "ib8"
          ? "IB MYP: балл по критерию до 8. Это не итоговая предметная оценка 1–7 и не сумма IB Diploma. Сохраним исходное значение без автоматического перевода в GPA."
          : scale === "100"
            ? "Процентная шкала сохраняется как есть: для сопоставления с GPA нужны правила вашего учебного заведения."
            : scale === "5"
              ? "Перевод в GPA / 4 приблизительный. Исходный балл сохраняется в профиле."
              : "Укажите свой средний балл по шкале GPA / 4."}
      </p>
    </div>
  );
}
