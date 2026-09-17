import type { QueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";

import { onBackendRecovered } from "./api/client";
import { setNavigator } from "./lib/nav";
import { getAccessToken } from "./lib/supabase";
import { router } from "./router";
import { useUi } from "./store/ui";

setNavigator((path) => void router.navigate(path));

export function App({ queryClient }: { queryClient: QueryClient }) {
  const theme = useUi((s) => s.theme);

  useEffect(() => {
    // Start the anonymous session silently on first load (no login screen).
    getAccessToken().catch(() => undefined);
    // When the backend comes back after an outage, refresh everything.
    return onBackendRecovered(() => void queryClient.invalidateQueries());
  }, [queryClient]);

  return (
    <>
      <RouterProvider router={router} />
      <Toaster position="top-center" theme={theme} richColors closeButton />
    </>
  );
}
