import { cn } from "@/lib/utils";
export function Logo({
  className,
  light = false,
}: {
  className?: string;
  light?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2.5",
        light ? "text-white" : "text-foreground",
        className,
      )}
      aria-label="applyra"
    >
      <svg
        viewBox="0 0 40 40"
        className="h-10 w-10 shrink-0 text-primary"
        aria-hidden="true"
      >
        <rect width="40" height="40" rx="12" fill="currentColor" />
        <path
          d="M10 29 20 10 30 29M15 22h10"
          fill="none"
          stroke="white"
          strokeWidth="2.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="text-2xl font-extrabold tracking-tight">
        applyra<span className="text-primary">.</span>
      </span>
    </span>
  );
}
