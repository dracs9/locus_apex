import { Check } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { t } from "@/i18n/ru";
import { cn } from "@/lib/utils";

const PATHS = ["/passport", "/recommendations", "/compare", "/roadmap", "/today"];

/** Main-path stepper: Passport → Universities → Compare → Plan → Today. */
export function Stepper() {
  const { pathname } = useLocation();
  const current = PATHS.indexOf(pathname);
  if (current < 0) return null;
  return (
    <nav aria-label="Шаги маршрута" className="mb-5 overflow-hidden">
      <ol className="flex items-center gap-1">
        {PATHS.map((path, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <li key={path} className="flex min-w-0 flex-1 items-center gap-1">
              <Link
                to={path}
                aria-current={active ? "step" : undefined}
                className={cn("flex min-w-0 items-center gap-1.5 rounded-full py-1 pr-1 text-xs font-semibold", active ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
              >
                <span
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px]",
                    active && "border-primary bg-primary text-primary-foreground",
                    done && "border-primary/40 bg-primary/10 text-primary",
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                </span>
                <span className={cn("truncate", !active && "hidden sm:inline")}>{t.stepper[i]}</span>
              </Link>
              {i < PATHS.length - 1 && <span className={cn("h-px min-w-2 flex-1", done ? "bg-primary/40" : "bg-border")} aria-hidden />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
