import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL ?? "";
// Prefer publishable key (sb_publishable_...) — safe for frontend. Fall back to anon key for legacy.
const publishableKey =
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? import.meta.env.VITE_SUPABASE_ANON_KEY ?? "";

export const supabase = createClient(url, publishableKey);
