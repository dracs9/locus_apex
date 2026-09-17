import { create } from "zustand";
import { persist } from "zustand/middleware";

interface NetworkState {
  offline: boolean;
  slow: boolean;
  setOffline: (v: boolean) => void;
  setSlow: (v: boolean) => void;
}

/** Backend reachability, driven by api/client.ts. */
export const useNetwork = create<NetworkState>((set) => ({
  offline: false,
  slow: false,
  setOffline: (offline) => set({ offline }),
  setSlow: (slow) => set({ slow }),
}));

interface UiState {
  compareIds: string[];
  toggleCompare: (id: string) => void;
  setCompare: (ids: string[]) => void;
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
}

export const useUi = create<UiState>()(
  persist(
    (set, get) => ({
      compareIds: [],
      toggleCompare: (id) => {
        const ids = get().compareIds;
        if (ids.includes(id)) set({ compareIds: ids.filter((x) => x !== id) });
        else if (ids.length < 3) set({ compareIds: [...ids, id] });
      },
      setCompare: (compareIds) => set({ compareIds: compareIds.slice(0, 3) }),
      theme: document.documentElement.classList.contains("dark") ? "dark" : "light",
      setTheme: (theme) => {
        document.documentElement.classList.toggle("dark", theme === "dark");
        try {
          localStorage.setItem("theme", theme);
        } catch {
          /* storage may be unavailable */
        }
        set({ theme });
      },
    }),
    { name: "ui", partialize: (s) => ({ compareIds: s.compareIds }) },
  ),
);
