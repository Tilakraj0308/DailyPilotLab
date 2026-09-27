import { publicEnv } from "./env";

/**
 * Backend API base URL supplied by the active local or EAS environment.
 */
export function getApiUrl(): string {
  return publicEnv.apiUrl;
}
