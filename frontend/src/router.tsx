import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { Changes } from "./pages/Changes";
import { Compare } from "./pages/Compare";
import { History } from "./pages/History";
import { Interests } from "./pages/Interests";
import { Landing } from "./pages/Landing";
import { Mentor } from "./pages/Mentor";
import { Onboarding } from "./pages/Onboarding";
import { Passport } from "./pages/Passport";
import { Recommendations } from "./pages/Recommendations";
import { Roadmap } from "./pages/Roadmap";
import { Settings } from "./pages/Settings";
import { Today } from "./pages/Today";
import { University } from "./pages/University";

export const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  { path: "/onboarding", element: <Onboarding /> },
  {
    element: <AppShell />,
    children: [
      { path: "/passport", element: <Passport /> },
      { path: "/interests", element: <Interests /> },
      { path: "/recommendations", element: <Recommendations /> },
      { path: "/university/:id", element: <University /> },
      { path: "/compare", element: <Compare /> },
      { path: "/roadmap", element: <Roadmap /> },
      { path: "/mentor", element: <Mentor /> },
      { path: "/today", element: <Today /> },
      { path: "/history", element: <History /> },
      { path: "/changes", element: <Changes /> },
      { path: "/settings", element: <Settings /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
