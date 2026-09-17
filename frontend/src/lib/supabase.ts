import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** Supabase is used ONLY for the anonymous session. All data goes through the FastAPI backend. */
export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey, { auth: { persistSession: true, autoRefreshToken: true } }) : null;

let pending: Promise<string | null> | null = null;

/** Returns an access token, silently signing in anonymously on first visit. */
export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  if (data.session) return data.session.access_token;
  if (!pending) {
    pending = supabase.auth
      .signInAnonymously()
      .then(({ data: signIn, error }) => {
        if (error) throw error;
        return signIn.session?.access_token ?? null;
      })
      .finally(() => {
        pending = null;
      });
  }
  return pending;
}
