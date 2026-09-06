import { Platform } from "react-native";

/**
 * Backend API base URL (same rules as AuthContext — LAN IP for devices).
 */
export function getApiUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  let url = envUrl || "http://localhost:8000";

  if (Platform.OS === "android" && !envUrl) {
    url = "http://10.0.2.2:8000";
  }

  return url.replace(/\/+$/, "");
}
