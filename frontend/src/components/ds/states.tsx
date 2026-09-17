import { CloudOff, Inbox, Loader2, RefreshCw, WifiOff } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { useNetwork } from "@/store/ui";

export function EmptyState({ title, text, action, icon }: { title: string; text?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-10 text-center">
      <div className="rounded-full bg-muted p-3 text-muted-foreground">{icon ?? <Inbox className="h-6 w-6" />}</div>
      <p className="font-semibold">{title}</p>
      {text && <p className="max-w-sm text-sm text-muted-foreground">{text}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-lg border border-blocker/30 bg-blocker-soft/40 px-6 py-10 text-center">
      <CloudOff className="h-7 w-7 text-blocker" />
      <p className="font-semibold">{t.states.errorTitle}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{message ?? t.states.errorText}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          <RefreshCw /> {t.common.retry}
        </Button>
      )}
    </div>
  );
}

/** Offline (cached data shown) and "waking the server" banners. */
export function NetworkBanners() {
  const { offline, slow } = useNetwork();
  if (offline) {
    return (
      <div role="status" className="flex items-center gap-2 bg-risk-soft px-4 py-2 text-sm font-medium text-risk">
        <WifiOff className="h-4 w-4 shrink-0" />
        {t.states.offline}
      </div>
    );
  }
  if (slow) {
    return (
      <div role="status" className="flex items-center gap-2 bg-target-soft px-4 py-2 text-sm font-medium text-target">
        <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
        {t.states.waking}
      </div>
    );
  }
  return null;
}

export function CardsSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label={t.common.loading}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="space-y-3 rounded-lg border bg-card p-4">
          <div className="flex justify-between gap-3">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-5 w-16" />
          </div>
          <Skeleton className="h-4 w-1/3" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-6 w-32" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
      <CardsSkeleton />
    </div>
  );
}
