import { Logo } from "@/components/brand/Logo";
import {
  CalendarCheck2,
  Compass,
  GitCompareArrows,
  History,
  Home,
  IdCard,
  ListChecks,
  Plus,
  Settings,
  Sparkles,
} from "lucide-react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { isNotFound } from "@/api/client";
import { useProfile, useUniversities } from "@/api/hooks";
import {
  AddAchievementSheet,
  useAchievementSheet,
} from "@/components/achievements/AddAchievementSheet";
import {
  NetworkBanners,
  PageSkeleton,
  ErrorState,
} from "@/components/ds/states";
import { Stepper } from "@/components/ds/Stepper";
import { ProfileEditorSheet } from "@/components/profile/ProfileEditorSheet";
import { t } from "@/i18n/ru";
import { countryName } from "@/lib/format";
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
  { to: "/interests", label: "Мои интересы", icon: Compass },
  { to: "/compare", label: t.nav.compare, icon: GitCompareArrows },
  { to: "/roadmap", label: t.nav.plan, icon: CalendarCheck2 },
  { to: "/mentor", label: t.nav.mentor, icon: Sparkles },
  { to: "/today", label: t.nav.today, icon: Home },
  { to: "/history", label: t.nav.achievements, icon: ListChecks },
  { to: "/changes", label: t.nav.changes, icon: History },
  { to: "/settings", label: t.nav.settings, icon: Settings },
];

function Sidebar() {
  const { search, pathname } = useLocation();
  const catalog = useUniversities();
  const countries = [
    ...new Set([
      "US",
      "HK",
      "CN",
      "IT",
      ...(catalog.data ?? []).map((u) => u.country),
    ]),
  ];
  const selectedCountry = new URLSearchParams(search).get("country");
  return (
    <aside className="sticky top-0 hidden h-dvh overflow-y-auto w-60 shrink-0 flex-col border-r bg-card px-4 py-7 md:flex">
      <NavLink to="/" className="mb-6 flex items-center gap-2 px-3">
        <Logo />
      </NavLink>
      <nav className="flex flex-col gap-1">
        {SIDEBAR.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-semibold transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-5 border-t pt-4">
        <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Страны
        </p>
        <nav
          aria-label="Университеты по странам"
          className="mt-2 flex flex-col gap-1"
        >
          {countries.map((code) => (
            <Link
              key={code}
              to={`/recommendations?country=${code}`}
              aria-current={
                pathname === "/recommendations" && selectedCountry === code
                  ? "page"
                  : undefined
              }
              className={cn(
                "rounded-md px-3 py-2 text-sm",
                pathname === "/recommendations" && selectedCountry === code
                  ? "bg-primary/10 font-semibold text-primary"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              {countryName(code)}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}

function BottomTabBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      aria-label="Навигация"
    >
      <ul className="grid grid-cols-4">
        {TABS.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-semibold",
                  isActive ? "text-primary" : "text-muted-foreground",
                )
              }
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
  else if (profile.isError && isNotFound(profile.error))
    return <Navigate to="/onboarding" replace />;
  else if (profile.isError && !profile.data)
    content = <ErrorState onRetry={() => profile.refetch()} />;

  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="sticky top-0 z-30">
          <NetworkBanners />
        </div>
        <main
          key={pathname}
          className="mx-auto w-full max-w-7xl flex-1 animate-fade-up px-4 pb-safe pt-5 md:px-8 md:pb-12 md:pt-8"
        >
          <Stepper />
          {content}
        </main>
      </div>
      <BottomTabBar />
      {/* the chat has its own input at the bottom, where the button would cover it */}
      {profile.data && pathname !== "/mentor" && <Fab />}
      <AddAchievementSheet />
      {profile.data && <ProfileEditorSheet />}
    </div>
  );
}
