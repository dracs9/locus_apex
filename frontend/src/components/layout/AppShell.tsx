import { CalendarCheck2, Compass, GitCompareArrows, History, Home, IdCard, ListChecks, Plus, Settings, Sparkles } from "lucide-react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { isNotFound } from "@/api/client";
import { useProfile } from "@/api/hooks";
import { AddAchievementSheet, useAchievementSheet } from "@/components/achievements/AddAchievementSheet";
import { NetworkBanners, PageSkeleton, ErrorState } from "@/components/ds/states";
import { Stepper } from "@/components/ds/Stepper";
import { ProfileEditorSheet } from "@/components/profile/ProfileEditorSheet";
import { t } from "@/i18n/ru";
import { cn } from "@/lib/utils";

const TABS = [
  { to: "/today", label: t.nav.today, icon: Home },
  { to: "/recommendations", label: t.nav.universities, icon: Compass },
  { to: "/roadmap", label: t.nav.plan, icon: CalendarCheck2 },
  { to: "/passport", label: t.nav.profile, icon: IdCard },
];

const SIDEBAR = [
  { to: "/passport", label: t.nav.passport, icon: IdCard },
  { to: "/recommendations", label: t.nav.universities, icon: Compass },
  { to: "/compare", label: t.nav.compare, icon: GitCompareArrows },
  { to: "/roadmap", label: t.nav.plan, icon: CalendarCheck2 },
  { to: "/today", label: t.nav.today, icon: Home },
  { to: "/history", label: t.nav.achievements, icon: ListChecks },
  { to: "/changes", label: t.nav.changes, icon: History },
  { to: "/settings", label: t.nav.settings, icon: Settings },
];

function Sidebar() {
  return (
    <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r bg-card/60 px-3 py-5 md:flex">
      <NavLink to="/" className="mb-6 flex items-center gap-2 px-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Sparkles className="h-5 w-5" />
        </span>
        <span className="font-display text-lg font-bold">{t.app.name}</span>
      </NavLink>
      <nav className="flex flex-col gap-1">
        {SIDEBAR.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn("flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-semibold transition-colors", isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground")
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

function BottomTabBar() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden" aria-label="Навигация">
      <ul className="grid grid-cols-4">
        {TABS.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) => cn("flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-semibold", isActive ? "text-primary" : "text-muted-foreground")}
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function Fab() {
  const openNew = useAchievementSheet((s) => s.openNew);
  return (
    <button
      type="button"
      onClick={() => openNew()}
      className="fixed bottom-20 right-4 z-40 flex h-14 items-center gap-2 rounded-full bg-accent px-5 font-bold text-accent-foreground shadow-lg transition-transform active:scale-95 md:bottom-6 md:right-6"
      aria-label={t.achievements.add}
    >
      <Plus className="h-5 w-5" />
      <span className="hidden sm:inline">{t.today.addAchievement}</span>
    </button>
  );
}

/** App layout for pages after onboarding. Redirects to onboarding when there is no profile yet. */
export function AppShell() {
  const profile = useProfile();
  const { pathname } = useLocation();

  let content = <Outlet />;
  if (profile.isPending) content = <PageSkeleton />;
  else if (profile.isError && isNotFound(profile.error)) return <Navigate to="/onboarding" replace />;
  else if (profile.isError && !profile.data) content = <ErrorState onRetry={() => profile.refetch()} />;

  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="sticky top-0 z-30">
          <NetworkBanners />
        </div>
        <main key={pathname} className="mx-auto w-full max-w-4xl flex-1 animate-fade-up px-4 pb-safe pt-5 md:px-8 md:pb-12 md:pt-8">
          <Stepper />
          {content}
        </main>
      </div>
      <BottomTabBar />
      {profile.data && <Fab />}
      <AddAchievementSheet />
      {profile.data && <ProfileEditorSheet />}
    </div>
  );
}
