import { Platform } from "react-native";

/**
 * Backend API base URL (same rules as AuthContext — LAN IP for devices).
 */
export function getApiUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_URL;

  if (!Platform.OS || Platform.OS === "web") {
    return envUrl || "http://localhost:8000";
  }
  if (envUrl) {
    return envUrl;
  }
  if (Platform.OS === "android") {
    return "http://10.0.2.2:8000";
  }
  return "http://localhost:8000";
}
