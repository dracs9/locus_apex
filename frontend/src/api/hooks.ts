import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { t } from "@/i18n/ru";
import { diffSummary } from "@/lib/format";
import { navigateTo } from "@/lib/nav";
import { useNetwork } from "@/store/ui";

import { api, apiBlob, ApiError } from "./client";
import type {
  ActionResult,
  AchievementCreated,
  AchievementIn,
  Attachment,
  AchievementPatch,
  ChancePoint,
  ComputeResponse,
  Essay,
  EssaySummary,
  ExplainOut,
  LatestChanges,
  Major,
  MentorMessage,
  MentorReply,
  PassportOut,
  RecommendedEssay,
  Priorities,
  Profile,
  ProfileIn,
  RecommendationResult,
  Roadmap,
  RoadmapTextOut,
  StepIn,
  StepPatch,
  Suggestion,
  University,
} from "./types";

export const keys = {
  profile: ["me", "profile"] as const,
  recommendations: ["me", "recommendations"] as const,
  roadmap: ["me", "roadmap"] as const,
  suggestions: ["me", "roadmap", "suggestions"] as const,
  changes: ["me", "changes"] as const,
  favorites: ["me", "favorites"] as const,
  chanceHistory: (ids: string) => ["me", "chance-history", ids] as const,
  passport: ["me", "ai", "passport"] as const,
  explain: (id: string) => ["me", "ai", "explain", id] as const,
  roadmapText: (ids: string) => ["me", "ai", "roadmap-text", ids] as const,
  mentor: ["me", "mentor"] as const,
  universities: ["catalog", "universities"] as const,
  majors: ["catalog", "majors"] as const,
  essays: ["essays"] as const,
  essay: (id: string) => ["essays", id] as const,
  recommendedEssays: ["me", "essays", "recommended"] as const,
};

const noRetryOn404 = (count: number, error: unknown) =>
  !(error instanceof ApiError && (error.status === 404 || error.status === 401)) && count < 2;

// --- catalog ---------------------------------------------------------------

export function useUniversities() {
  return useQuery({
    queryKey: keys.universities,
    queryFn: () => api<University[]>("/catalog/universities", { auth: false }),
    staleTime: 5 * 60 * 1000, // catalog changes only on re-seed; keep it short so new data shows up quickly
  });
}

export function useUniversityMap() {
  const q = useUniversities();
  const map = new Map((q.data ?? []).map((u) => [u.id, u]));
  return { ...q, map };
}

export function useMajors() {
  return useQuery({
    queryKey: keys.majors,
    queryFn: () => api<Major[]>("/catalog/majors", { auth: false }),
    staleTime: 5 * 60 * 1000, // catalog changes only on re-seed; keep it short so new data shows up quickly
  });
}

// --- essays --------------------------------------------------------------

export function useEssays() {
  return useQuery({
    queryKey: keys.essays,
    queryFn: () => api<EssaySummary[]>("/essays", { auth: false }),
    staleTime: 60 * 60 * 1000, // the collection changes only on a new deploy
  });
}

export function useEssay(id: string) {
  return useQuery({
    queryKey: keys.essay(id),
    queryFn: () => api<Essay>(`/essays/${encodeURIComponent(id)}`, { auth: false }),
    staleTime: 60 * 60 * 1000,
    retry: noRetryOn404,
  });
}

export function useRecommendedEssays() {
  return useQuery({
    queryKey: keys.recommendedEssays,
    queryFn: () => api<RecommendedEssay[]>("/me/essays/recommended"),
    retry: noRetryOn404,
  });
}

// --- me --------------------------------------------------------------------

export function useProfile() {
  return useQuery({ queryKey: keys.profile, queryFn: () => api<Profile>("/me/profile"), retry: noRetryOn404 });
}

export function useRecommendations(enabled = true) {
  return useQuery({
    queryKey: keys.recommendations,
    queryFn: () => api<RecommendationResult>("/me/recommendations"),
    retry: noRetryOn404,
    enabled,
  });
}

export function useRoadmap(enabled = true) {
  return useQuery({ queryKey: keys.roadmap, queryFn: () => api<Roadmap>("/me/roadmap"), retry: noRetryOn404, enabled });
}

export function useSuggestions(enabled = true) {
  return useQuery({
    queryKey: keys.suggestions,
    queryFn: () => api<Suggestion[]>("/me/roadmap/suggestions"),
    retry: noRetryOn404,
    enabled,
  });
}

export function useLatestChanges() {
  return useQuery({ queryKey: keys.changes, queryFn: () => api<LatestChanges>("/me/changes/latest"), retry: noRetryOn404 });
}

export function useFavorites(enabled = true) {
  return useQuery({ queryKey: keys.favorites, queryFn: () => api<string[]>("/me/favorites"), retry: noRetryOn404, enabled });
}

export function useChanceHistory(ids: string[] = []) {
  const joined = ids.join(",");
  return useQuery({
    queryKey: keys.chanceHistory(joined),
    queryFn: () => api<ChancePoint[]>(`/me/chance-history${joined ? `?ids=${encodeURIComponent(joined)}` : ""}`),
    retry: noRetryOn404,
  });
}

export function usePassportText(enabled = true) {
  return useQuery({
    queryKey: keys.passport,
    queryFn: () => api<PassportOut>("/ai/passport", { method: "POST" }),
    retry: noRetryOn404,
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

export function useExplain(universityId: string, enabled = true) {
  return useQuery({
    queryKey: keys.explain(universityId),
    queryFn: () => api<ExplainOut>("/ai/explain", { method: "POST", body: { university_id: universityId } }),
    retry: noRetryOn404,
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

export function useRoadmapText(stepIds: string[]) {
  const joined = stepIds.join(",");
  return useQuery({
    queryKey: keys.roadmapText(joined),
    queryFn: () => api<RoadmapTextOut>("/ai/roadmap-text", { method: "POST", body: { step_ids: stepIds } }),
    enabled: stepIds.length > 0,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}

/** How a country outside the profile would look for this student: stateless /preview, nothing is saved. */
export function useCountryPreview(profile: Profile | undefined, country: string | null) {
  const outside = !!profile && !!country && !profile.countries.includes(country);
  return usePreview(outside ? { ...profile!, countries: [country!] } : undefined, outside ? profile!.priorities : null);
}

export function usePreview(profile: Profile | undefined, priorities: Priorities | null) {
  return useQuery({
    queryKey: ["preview", profile?.created_at, profile, priorities],
    queryFn: () =>
      api<RecommendationResult>("/preview", {
        method: "POST",
        auth: false,
        body: { profile, priorities_override: priorities },
      }),
    enabled: !!profile && !!priorities,
    placeholderData: (prev) => prev,
    staleTime: 60 * 1000,
  });
}

// --- mutations -------------------------------------------------------------

/** Puts a fresh ComputeResponse into the cache, refreshes dependants and shows the "route updated" toast. */
export function applyCompute(qc: QueryClient, res: ComputeResponse, { silent = false } = {}) {
  qc.setQueryData(keys.recommendations, res.result);
  qc.setQueryData(keys.roadmap, res.roadmap);
  void qc.invalidateQueries({ queryKey: keys.profile });
  void qc.invalidateQueries({ queryKey: keys.changes });
  void qc.invalidateQueries({ queryKey: keys.favorites });
  void qc.invalidateQueries({ queryKey: ["me", "chance-history"] });
  void qc.invalidateQueries({ queryKey: ["me", "ai"] });
  void qc.invalidateQueries({ queryKey: keys.recommendedEssays });
  if (silent || !res.diff) return;
  const summary = diffSummary(res.diff);
  toast.success(summary ? t.changes.toast(summary) : t.changes.toastNoChange, {
    description: res.diff.cause,
    action: { label: t.changes.toastAction, onClick: () => navigateTo("/changes") },
    duration: 6000,
  });
}

function onMutationError(e: unknown) {
  toast.error(e instanceof ApiError ? e.message : t.errors.generic);
}

function useComputeMutation<V, R extends ComputeResponse = ComputeResponse>(fn: (v: V) => Promise<R>, opts: { silent?: boolean } = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: V) => {
      if (useNetwork.getState().offline) return Promise.reject(new ApiError(0, "NETWORK", t.common.offlineEditsDisabled));
      return fn(v);
    },
    // A 503 means the backend lost its database connection mid-request, so the transaction
    // rolled back and nothing was written — retrying once is safe and saves the user a toast.
    retry: (attempt, e) => e instanceof ApiError && e.status === 503 && attempt < 1,
    onSuccess: (res) => applyCompute(qc, res, opts),
    onError: onMutationError,
  });
}

export function useSaveProfile(opts: { silent?: boolean } = {}) {
  return useComputeMutation((body: ProfileIn) => api<ComputeResponse>("/me/profile", { method: "PUT", body }), opts);
}

export function useAddAchievement() {
  return useComputeMutation((body: AchievementIn) => api<AchievementCreated>("/me/achievements", { method: "POST", body }));
}

// --- attachments (photos / links): they don't affect scoring, so only the profile is refreshed ---

function useAttachmentMutation<V, R>(fn: (v: V) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: V) => {
      if (useNetwork.getState().offline) return Promise.reject(new ApiError(0, "NETWORK", t.common.offlineEditsDisabled));
      return fn(v);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.profile }),
    onError: onMutationError,
  });
}

export function useAddLink() {
  return useAttachmentMutation(({ achievementId, url, title }: { achievementId: string; url: string; title?: string }) =>
    api<Attachment>(`/me/achievements/${achievementId}/attachments/link`, { method: "POST", body: { url, title: title || null } }),
  );
}

export function useUploadPhoto() {
  return useAttachmentMutation(({ achievementId, file }: { achievementId: string; file: Blob }) => {
    const form = new FormData();
    form.append("file", file, file instanceof File ? file.name : "photo.jpg");
    return api<Attachment>(`/me/achievements/${achievementId}/attachments/photo`, { method: "POST", body: form });
  });
}

export function useDeleteAttachment() {
  return useAttachmentMutation(({ achievementId, attachmentId }: { achievementId: string; attachmentId: string }) =>
    api<void>(`/me/achievements/${achievementId}/attachments/${attachmentId}`, { method: "DELETE" }),
  );
}

export function usePatchAchievement() {
  return useComputeMutation(({ id, body }: { id: string; body: AchievementPatch }) =>
    api<ComputeResponse>(`/me/achievements/${id}`, { method: "PATCH", body }),
  );
}

export function useDeleteAchievement() {
  return useComputeMutation((id: string) => api<ComputeResponse>(`/me/achievements/${id}`, { method: "DELETE" }));
}

export function useToggleFavorite() {
  return useComputeMutation(({ id, on }: { id: string; on: boolean }) =>
    api<ComputeResponse>(`/me/favorites/${id}`, { method: on ? "PUT" : "DELETE" }),
  );
}

export function useLoadDemo() {
  return useComputeMutation(() => api<ComputeResponse>("/me/demo", { method: "POST" }), { silent: true });
}

/** Plan edits return the whole plan; suggestions change too (added ones drop out), so they are refetched. */
function usePlanMutation<V>(fn: (v: V) => Promise<Roadmap>, optimistic?: (prev: Roadmap, v: V) => Roadmap) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: V) => {
      if (useNetwork.getState().offline) return Promise.reject(new ApiError(0, "NETWORK", t.common.offlineEditsDisabled));
      return fn(v);
    },
    onMutate: async (v: V) => {
      if (!optimistic) return { prev: undefined };
      await qc.cancelQueries({ queryKey: keys.roadmap, exact: true });
      const prev = qc.getQueryData<Roadmap>(keys.roadmap);
      if (prev) qc.setQueryData(keys.roadmap, optimistic(prev, v));
      return { prev };
    },
    onSuccess: (roadmap) => {
      qc.setQueryData(keys.roadmap, roadmap);
      void qc.invalidateQueries({ queryKey: keys.suggestions });
    },
    onError: (e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(keys.roadmap, ctx.prev);
      onMutationError(e);
    },
  });
}

export function useAddStep() {
  return usePlanMutation((body: StepIn) => api<Roadmap>("/me/roadmap/items", { method: "POST", body }));
}

export function usePatchStep() {
  return usePlanMutation(
    ({ id, ...body }: StepPatch & { id: string }) =>
      api<Roadmap>(`/me/roadmap/items/${encodeURIComponent(id)}`, { method: "PATCH", body }),
    (prev, { id, ...patch }) => ({
      ...prev,
      steps: prev.steps.map((s) =>
        s.id === id ? { ...s, ...Object.fromEntries(Object.entries(patch).filter(([, v]) => v != null)) } : s,
      ),
    }),
  );
}

export function useDeleteStep() {
  return usePlanMutation(
    (id: string) => api<Roadmap>(`/me/roadmap/items/${encodeURIComponent(id)}`, { method: "DELETE" }),
    (prev, id) => ({ ...prev, steps: prev.steps.filter((s) => s.id !== id) }),
  );
}

// --- AI mentor ---------------------------------------------------------------

export function useMentor() {
  return useQuery({ queryKey: keys.mentor, queryFn: () => api<MentorMessage[]>("/ai/mentor"), retry: noRetryOn404 });
}

function offlineGuard<T>(fn: () => Promise<T>): Promise<T> {
  if (useNetwork.getState().offline) return Promise.reject(new ApiError(0, "NETWORK", t.common.offlineEditsDisabled));
  return fn();
}

/** Sends a message; the user's bubble shows at once and is replaced by the saved pair from the server. */
export function useSendMentor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => offlineGuard(() => api<MentorReply>("/ai/mentor", { method: "POST", body: { text } })),
    onMutate: async (text) => {
      await qc.cancelQueries({ queryKey: keys.mentor });
      const prev = qc.getQueryData<MentorMessage[]>(keys.mentor) ?? [];
      const pending: MentorMessage = {
        id: `pending-${Date.now()}`,
        role: "user",
        text,
        actions: [],
        generated: false,
        created_at: new Date().toISOString(),
      };
      qc.setQueryData(keys.mentor, [...prev, pending]);
      return { prev };
    },
    onSuccess: (res, _text, ctx) => {
      // Drop optimistic bubbles (one may survive a closed tab in the persisted cache), then resync:
      // sending cancels an in-flight refetch, so the cached list can be missing earlier replies.
      const saved = (ctx?.prev ?? []).filter((m) => !m.id.startsWith("pending-"));
      qc.setQueryData(keys.mentor, [...saved, ...res.messages]);
      void qc.invalidateQueries({ queryKey: keys.mentor });
    },
    onError: (e, _text, ctx) => {
      if (ctx) qc.setQueryData(keys.mentor, ctx.prev);
      onMutationError(e);
    },
  });
}

export function useMentorAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ messageId, index, apply }: { messageId: string; index: number; apply: boolean }) =>
      offlineGuard(() =>
        api<ActionResult>(`/ai/mentor/${messageId}/actions/${index}`, { method: "POST", body: { apply } }),
      ),
    onSuccess: (res) => {
      qc.setQueryData<MentorMessage[]>(keys.mentor, (list) =>
        (list ?? []).map((m) => (m.id === res.message.id ? res.message : m)),
      );
      if (res.roadmap) {
        qc.setQueryData(keys.roadmap, res.roadmap);
        void qc.invalidateQueries({ queryKey: keys.suggestions });
      }
    },
    onError: (e) => {
      // a failed apply marks the proposal on the server; refetch to show it
      void qc.invalidateQueries({ queryKey: keys.mentor });
      onMutationError(e);
    },
  });
}

export function useClearMentor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => offlineGuard(() => api<void>("/ai/mentor", { method: "DELETE" })),
    onSuccess: () => qc.setQueryData(keys.mentor, []),
    onError: onMutationError,
  });
}

export function useReset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ ok: boolean }>("/me/reset", { method: "POST" }),
    onSuccess: () => {
      qc.removeQueries({ queryKey: ["me"] });
      qc.removeQueries({ queryKey: ["preview"] });
    },
    onError: onMutationError,
  });
}

export async function downloadIcs() {
  try {
    const blob = await apiBlob("/me/roadmap.ics");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "applyra-route.ics";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    onMutationError(e);
  }
}
