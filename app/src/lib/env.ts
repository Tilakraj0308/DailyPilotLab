function requirePublicEnv(name: string, value: string | undefined): string {
  const normalized = value?.trim();
  if (!normalized) {
    throw new Error(
      `Missing ${name}. Configure it in app/.env for local development or in the selected EAS environment for cloud builds.`,
    );
  }
  return normalized;
}

/**
 * Public client configuration embedded by Expo at bundle time.
 * These values are visible in the compiled application and must never contain
 * server-only credentials.
 */
export const publicEnv = Object.freeze({
  apiUrl: requirePublicEnv(
    "EXPO_PUBLIC_API_URL",
    process.env.EXPO_PUBLIC_API_URL,
  ).replace(/\/+$/, ""),
  supabaseUrl: requirePublicEnv(
    "EXPO_PUBLIC_SUPABASE_URL",
    process.env.EXPO_PUBLIC_SUPABASE_URL,
  ),
  supabaseAnonKey: requirePublicEnv(
    "EXPO_PUBLIC_SUPABASE_ANON_KEY",
    process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY,
  ),
});
